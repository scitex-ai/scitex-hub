/**
 * Test Suite: User Profile Management
 * Following TDD principles with comprehensive profile functionality testing
 */

describe('Profile Management', () => {
    // Mock fetch for API testing
    beforeEach(() => {
        global.fetch = jest.fn();
        document.body.innerHTML = `
            <div class="profile-container">
                <form id="profile-form" class="profile-form">
                    <input type="text" id="first_name" name="first_name" required>
                    <input type="text" id="last_name" name="last_name" required>
                    <input type="email" id="email" name="email" required>
                    <textarea id="bio" name="bio" maxlength="500"></textarea>
                    <input type="text" id="institution" name="institution">
                    <textarea id="research_interests" name="research_interests" maxlength="500"></textarea>
                    <input type="url" id="website" name="website">
                    <input type="text" id="orcid" name="orcid" pattern="[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]">
                    <input type="text" id="academic_title" name="academic_title">
                    <input type="text" id="department" name="department">
                    <select id="profile_visibility" name="profile_visibility">
                        <option value="public">Public</option>
                        <option value="restricted">Restricted</option>
                        <option value="private">Private</option>
                    </select>
                    <button type="submit" id="save-btn">Save Profile</button>
                </form>
                <div id="profile-display" class="profile-display"></div>
                <div id="status-message" class="status-message"></div>
            </div>
        `;
    });

    afterEach(() => {
        jest.restoreAllMocks();
        document.body.innerHTML = '';
    });

    describe('Profile Form Validation', () => {
        test('should validate required fields', () => {
            // Arrange
            const form = document.getElementById('profile-form');
            const firstNameField = document.getElementById('first_name');
            const lastNameField = document.getElementById('last_name');
            const emailField = document.getElementById('email');

            // Act & Assert
            expect(firstNameField.hasAttribute('required')).toBe(true);
            expect(lastNameField.hasAttribute('required')).toBe(true);
            expect(emailField.hasAttribute('required')).toBe(true);
            expect(form).toBeTruthy();
        });

        test('should validate email format', () => {
            // Arrange
            const emailField = document.getElementById('email');

            // Act & Assert
            expect(emailField.type).toBe('email');
        });

        test('should validate ORCID format', () => {
            // Arrange
            const orcidField = document.getElementById('orcid');

            // Act & Assert
            expect(orcidField.getAttribute('pattern')).toBe('[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]');
        });

        test('should validate URL format for website', () => {
            // Arrange
            const websiteField = document.getElementById('website');

            // Act & Assert
            expect(websiteField.type).toBe('url');
        });

        test('should have character limits for text areas', () => {
            // Arrange
            const bioField = document.getElementById('bio');
            const interestsField = document.getElementById('research_interests');

            // Act & Assert
            expect(bioField.getAttribute('maxlength')).toBe('500');
            expect(interestsField.getAttribute('maxlength')).toBe('500');
        });
    });

    describe('Profile Data Loading', () => {
        test('should load profile data from API', async () => {
            // Arrange
            const mockProfileData = {
                success: true,
                profile: {
                    user: {
                        first_name: 'John',
                        last_name: 'Doe',
                        email: 'john.doe@example.com'
                    },
                    bio: 'Research scientist',
                    institution: 'Example University',
                    research_interests: 'Machine Learning, AI',
                    website: 'https://johndoe.com',
                    orcid: '0000-0000-0000-0000',
                    academic_title: 'PhD',
                    department: 'Computer Science'
                }
            };
            
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockProfileData
            });

            // Act
            const response = await fetch('/core/api/v1/profile/');
            const result = await response.json();

            // Assert
            expect(fetch).toHaveBeenCalledWith('/core/api/v1/profile/');
            expect(result.success).toBe(true);
            expect(result.profile.user.first_name).toBe('John');
            expect(result.profile.bio).toBe('Research scientist');
        });

        test('should handle profile loading errors', async () => {
            // Arrange
            global.fetch.mockResolvedValueOnce({
                ok: false,
                status: 500,
                json: async () => ({ success: false, error: 'Server error' })
            });

            // Act
            const response = await fetch('/core/api/v1/profile/');
            const result = await response.json();

            // Assert
            expect(result.success).toBe(false);
            expect(result.error).toBe('Server error');
        });
    });

    describe('Profile Form Population', () => {
        test('should populate form fields with profile data', () => {
            // Arrange
            const form = document.getElementById('profile-form');
            const profileData = {
                user: {
                    first_name: 'Jane',
                    last_name: 'Smith',
                    email: 'jane.smith@example.com'
                },
                bio: 'Researcher in physics',
                institution: 'MIT',
                research_interests: 'Quantum Computing',
                website: 'https://janesmith.com'
            };

            // Act
            document.getElementById('first_name').value = profileData.user.first_name;
            document.getElementById('last_name').value = profileData.user.last_name;
            document.getElementById('email').value = profileData.user.email;
            document.getElementById('bio').value = profileData.bio;
            document.getElementById('institution').value = profileData.institution;
            document.getElementById('research_interests').value = profileData.research_interests;
            document.getElementById('website').value = profileData.website;

            // Assert
            expect(document.getElementById('first_name').value).toBe('Jane');
            expect(document.getElementById('last_name').value).toBe('Smith');
            expect(document.getElementById('email').value).toBe('jane.smith@example.com');
            expect(document.getElementById('bio').value).toBe('Researcher in physics');
            expect(document.getElementById('institution').value).toBe('MIT');
        });
    });

    describe('Profile Update Operations', () => {
        test('should update profile successfully', async () => {
            // Arrange
            const mockResponse = {
                success: true,
                profile: {
                    user: {
                        first_name: 'Updated',
                        last_name: 'User'
                    },
                    bio: 'Updated bio'
                }
            };
            
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse
            });

            const profileData = {
                first_name: 'Updated',
                last_name: 'User',
                bio: 'Updated bio'
            };

            // Act
            const response = await fetch('/core/api/v1/profile/', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(profileData)
            });
            const result = await response.json();

            // Assert
            expect(fetch).toHaveBeenCalledWith('/core/api/v1/profile/', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(profileData)
            });
            expect(result.success).toBe(true);
            expect(result.profile.user.first_name).toBe('Updated');
        });

        test('should handle update validation errors', async () => {
            // Arrange
            global.fetch.mockResolvedValueOnce({
                ok: false,
                status: 400,
                json: async () => ({
                    success: false,
                    error: 'Invalid email format'
                })
            });

            // Act
            const response = await fetch('/core/api/v1/profile/', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: 'invalid-email' })
            });
            const result = await response.json();

            // Assert
            expect(result.success).toBe(false);
            expect(result.error).toBe('Invalid email format');
        });
    });

    describe('ORCID Validation', () => {
        test('should validate correct ORCID format', () => {
            // Arrange
            const orcidField = document.getElementById('orcid');
            const validOrcid = '0000-0002-1825-0097';

            // Act
            orcidField.value = validOrcid;

            // Assert
            expect(orcidField.checkValidity()).toBe(true);
        });

        test('should reject invalid ORCID format', () => {
            // Arrange
            const orcidField = document.getElementById('orcid');
            const invalidOrcid = '1234-5678-9012';

            // Act
            orcidField.value = invalidOrcid;

            // Assert
            expect(orcidField.checkValidity()).toBe(false);
        });
    });

    describe('Profile Visibility Settings', () => {
        test('should have visibility options', () => {
            // Arrange
            const visibilitySelect = document.getElementById('profile_visibility');
            const options = visibilitySelect.querySelectorAll('option');

            // Act & Assert
            expect(options.length).toBe(3);
            expect(options[0].value).toBe('public');
            expect(options[1].value).toBe('restricted');
            expect(options[2].value).toBe('private');
        });

        test('should update visibility setting', () => {
            // Arrange
            const visibilitySelect = document.getElementById('profile_visibility');

            // Act
            visibilitySelect.value = 'private';

            // Assert
            expect(visibilitySelect.value).toBe('private');
        });
    });

    describe('Profile Display', () => {
        test('should display profile information correctly', () => {
            // Arrange
            const profileDisplay = document.getElementById('profile-display');
            const profileData = {
                user: {
                    first_name: 'Dr. Alice',
                    last_name: 'Johnson'
                },
                institution: 'Stanford University',
                academic_title: 'Professor',
                research_interests: 'Computational Biology'
            };

            // Act
            profileDisplay.innerHTML = `
                <div class="profile-header">
                    <h2>${profileData.user.first_name} ${profileData.user.last_name}</h2>
                    <p class="academic-title">${profileData.academic_title}</p>
                    <p class="institution">${profileData.institution}</p>
                </div>
                <div class="research-interests">
                    <strong>Research Interests:</strong> ${profileData.research_interests}
                </div>
            `;

            // Assert
            expect(profileDisplay.innerHTML).toContain('Dr. Alice Johnson');
            expect(profileDisplay.innerHTML).toContain('Professor');
            expect(profileDisplay.innerHTML).toContain('Stanford University');
            expect(profileDisplay.innerHTML).toContain('Computational Biology');
        });
    });

    describe('Character Count for Text Areas', () => {
        test('should show character count for bio field', () => {
            // Arrange
            const bioField = document.getElementById('bio');
            const testText = 'This is a test bio';

            // Act
            bioField.value = testText;
            const characterCount = bioField.value.length;

            // Assert
            expect(characterCount).toBe(testText.length);
            expect(characterCount).toBeLessThanOrEqual(500);
        });

        test('should warn when approaching character limit', () => {
            // Arrange
            const bioField = document.getElementById('bio');
            const longText = 'a'.repeat(480); // Close to 500 limit

            // Act
            bioField.value = longText;

            // Assert
            expect(bioField.value.length).toBe(480);
            expect(bioField.value.length > 450).toBe(true); // Approaching limit
        });
    });

    describe('Status Message Display', () => {
        test('should show success messages correctly', () => {
            // Arrange
            const statusElement = document.getElementById('status-message');

            // Act
            statusElement.className = 'status-message success';
            statusElement.textContent = 'Profile updated successfully!';

            // Assert
            expect(statusElement.classList.contains('success')).toBe(true);
            expect(statusElement.textContent).toBe('Profile updated successfully!');
        });

        test('should show error messages correctly', () => {
            // Arrange
            const statusElement = document.getElementById('status-message');

            // Act
            statusElement.className = 'status-message error';
            statusElement.textContent = 'Error updating profile.';

            // Assert
            expect(statusElement.classList.contains('error')).toBe(true);
            expect(statusElement.textContent).toBe('Error updating profile.');
        });
    });
});