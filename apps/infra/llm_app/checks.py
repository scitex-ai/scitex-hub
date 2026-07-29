"""Boot-time guards for the in-product assistant's map of the app surface.

A skill that advertises an unresolvable route is not a cosmetic problem: the
string is aggregated verbatim into the LLM system prompt, so the assistant
hands users a URL that 301-redirects or 404s. Eight of eleven apps were in
that state before the mount became derived.

Deriving the URL prevents drift going forward; this check is what makes the
drift *unshippable* rather than merely unlikely — it fails `manage.py check`,
so it fails at boot and in CI instead of in a user's chat window.
"""

from django.core.checks import Error, register
from django.urls import NoReverseMatch, reverse


@register("urls")
def check_skill_routes_resolve(app_configs, **kwargs):
    """Every skill's declared ``url_route`` must resolve against the URLconf."""
    from .skills.registry import get_all_skills

    errors = []
    for app_name, skill in sorted(get_all_skills().items()):
        if not skill.url_route:
            # Deliberately unmounted app. It is omitted from the assistant's
            # module list rather than advertised — see Skill.resolve_url().
            continue
        try:
            reverse(skill.url_route)
        except NoReverseMatch as exc:
            errors.append(
                Error(
                    f"Skill {app_name!r} declares url_route "
                    f"{skill.url_route!r}, which does not resolve.",
                    hint=(
                        "The in-product assistant would advertise a dead URL "
                        "for this app. Point url_route at a route that exists "
                        "in config/urls.py (usually 'app_namespace:route_name'), "
                        "or set url_route='' if the app is intentionally not "
                        f"mounted. reverse() reported: {exc}"
                    ),
                    obj=f"{app_name}/skill.py",
                    id="llm_app.E001",
                )
            )
    return errors
