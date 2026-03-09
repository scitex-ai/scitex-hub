"""ORCID OAuth integration service"""

import requests
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from ..models import IntegrationConnection, ORCIDProfile, IntegrationLog


class ORCIDService:
    """Service for ORCID OAuth integration"""

    # ORCID API endpoints
    OAUTH_AUTHORIZE_URL = "https://orcid.org/oauth/authorize"
    OAUTH_TOKEN_URL = "https://orcid.org/oauth/token"
    API_BASE_URL = "https://pub.orcid.org/v3.0"

    def __init__(self, user=None, connection=None):
        self.user = user
        self.connection = connection
        self.client_id = getattr(settings, "ORCID_CLIENT_ID", None)
        self.client_secret = getattr(settings, "ORCID_CLIENT_SECRET", None)
        self.redirect_uri = getattr(settings, "ORCID_REDIRECT_URI", None)

    def get_authorization_url(self, state=None):
        """Generate ORCID OAuth authorization URL"""
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "scope": "/authenticate",
            "redirect_uri": self.redirect_uri,
        }
        if state:
            params["state"] = state

        url_params = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.OAUTH_AUTHORIZE_URL}?{url_params}"

    def exchange_code_for_token(self, code):
        """Exchange authorization code for access token"""
        try:
            response = requests.post(
                self.OAUTH_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                },
                headers={"Accept": "application/json"},
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "access_token": data["access_token"],
                    "token_type": data["token_type"],
                    "refresh_token": data.get("refresh_token"),
                    "expires_in": data.get("expires_in", 631138519),  # 20 years default
                    "scope": data["scope"],
                    "orcid": data["orcid"],
                    "name": data.get("name"),
                }
            else:
                raise Exception(f"Token exchange failed: {response.text}")

        except Exception as e:
            self._log_error("connect", str(e))
            raise

    def connect_user(self, token_data):
        """Connect user's ORCID account"""
        try:
            # Create or update connection
            connection, created = IntegrationConnection.objects.get_or_create(
                user=self.user,
                service="orcid",
                defaults={
                    "status": "active",
                    "external_user_id": token_data["orcid"],
                    "external_username": token_data.get("name", ""),
                },
            )

            # Set encrypted tokens
            connection.set_access_token(token_data["access_token"])
            if token_data.get("refresh_token"):
                connection.refresh_token = connection.encrypt_value(
                    token_data["refresh_token"]
                )

            # Set token expiration
            expires_in = token_data.get("expires_in", 631138519)
            connection.token_expires_at = timezone.now() + timedelta(seconds=expires_in)
            connection.status = "active"
            connection.save()

            self.connection = connection

            # Fetch and store profile data
            self.fetch_profile()

            self._log_activity("connect", "Successfully connected ORCID account")

            return connection

        except Exception as e:
            self._log_error("connect", str(e))
            raise

    def fetch_profile(self):
        """Fetch ORCID profile data"""
        if not self.connection:
            raise ValueError("No connection established")

        try:
            orcid_id = self.connection.external_user_id
            access_token = self.connection.get_access_token()

            # Fetch record
            response = requests.get(
                f"{self.API_BASE_URL}/{orcid_id}/record",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )

            if response.status_code != 200:
                raise Exception(f"Failed to fetch ORCID record: {response.text}")

            data = response.json()

            # Parse profile data
            person = data.get("person", {})
            name = person.get("name", {})
            biography = person.get("biography", {})

            given_names = name.get("given-names", {}).get("value", "")
            family_name = name.get("family-name", {}).get("value", "")
            bio_content = biography.get("content", "") if biography else ""

            # Parse affiliations
            affiliations = []
            employments = (
                data.get("activities-summary", {})
                .get("employments", {})
                .get("employment-summary", [])
            )
            for emp in employments:
                org = emp.get("organization", {})
                affiliations.append(
                    {
                        "name": org.get("name", ""),
                        "city": org.get("address", {}).get("city", ""),
                        "country": org.get("address", {}).get("country", ""),
                        "role": emp.get("role-title", ""),
                    }
                )

            current_institution = affiliations[0]["name"] if affiliations else ""

            # Parse keywords
            keywords = []
            keyword_data = person.get("keywords", {}).get("keyword", [])
            for kw in keyword_data:
                keywords.append(kw.get("content", ""))

            # Create or update profile
            profile, created = ORCIDProfile.objects.update_or_create(
                connection=self.connection,
                defaults={
                    "orcid_id": orcid_id,
                    "given_names": given_names,
                    "family_name": family_name,
                    "biography": bio_content,
                    "current_institution": current_institution,
                    "affiliations": affiliations,
                    "keywords": keywords,
                    "profile_url": f"https://orcid.org/{orcid_id}",
                },
            )

            self.connection.last_sync_at = timezone.now()
            self.connection.save()

            self._log_activity("sync", "Successfully synced ORCID profile")

            return profile

        except Exception as e:
            self._log_error("sync", str(e))
            raise

    def disconnect(self):
        """Disconnect ORCID account"""
        if not self.connection:
            raise ValueError("No connection to disconnect")

        try:
            self.connection.status = "inactive"
            self.connection.access_token = ""
            self.connection.refresh_token = ""
            self.connection.save()

            self._log_activity("disconnect", "Successfully disconnected ORCID account")

        except Exception as e:
            self._log_error("disconnect", str(e))
            raise

    def get_profile_data(self):
        """Get stored ORCID profile data"""
        if not self.connection:
            return None

        try:
            return self.connection.orcid_profile
        except ORCIDProfile.DoesNotExist:
            return None

    def _log_activity(self, action, details):
        """Log successful activity"""
        if self.connection:
            IntegrationLog.objects.create(
                connection=self.connection, action=action, details=details, success=True
            )

    def _log_error(self, action, error_message):
        """Log error"""
        if self.connection:
            IntegrationLog.objects.create(
                connection=self.connection,
                action=action,
                error_message=error_message,
                success=False,
            )
