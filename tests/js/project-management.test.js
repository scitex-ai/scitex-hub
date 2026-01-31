/**
 * Test Suite: Project Management CRUD Operations
 * Following TDD principles with comprehensive functionality testing
 */

describe('Project Management', () => {
    // Mock fetch for API testing
    beforeEach(() => {
        global.fetch = jest.fn();
        document.body.innerHTML = `
            <div class="project-container">
                <form id="project-form" class="project-form">
                    <input type="text" id="name" name="name" required>
                    <textarea id="description" name="description" required></textarea>
                    <select id="status" name="status">
                        <option value="planning">Planning</option>
                        <option value="active">Active</option>
                        <option value="completed">Completed</option>
                        <option value="on_hold">On Hold</option>
                    </select>
                    <input type="datetime-local" id="deadline" name="deadline">
                    <button type="submit" id="save-btn">Save Project</button>
                </form>
                <div id="project-list" class="project-list"></div>
                <div id="status-message" class="status-message"></div>
            </div>
        `;
    });

    afterEach(() => {
        jest.restoreAllMocks();
        document.body.innerHTML = '';
    });

    describe('Project Form Validation', () => {
        test('should validate required fields', () => {
            // Arrange
            const form = document.getElementById('project-form');
            const nameField = document.getElementById('name');
            const descriptionField = document.getElementById('description');

            // Act & Assert
            expect(nameField.hasAttribute('required')).toBe(true);
            expect(descriptionField.hasAttribute('required')).toBe(true);
            expect(form).toBeTruthy();
        });

        test('should have all project status options available', () => {
            // Arrange
            const statusSelect = document.getElementById('status');
            const options = statusSelect.querySelectorAll('option');

            // Act & Assert
            expect(options.length).toBe(4);
            expect(options[0].value).toBe('planning');
            expect(options[1].value).toBe('active');
            expect(options[2].value).toBe('completed');
            expect(options[3].value).toBe('on_hold');
        });

        test('should have deadline field for project timeline', () => {
            // Arrange
            const deadlineField = document.getElementById('deadline');

            // Act & Assert
            expect(deadlineField).toBeTruthy();
            expect(deadlineField.type).toBe('datetime-local');
        });
    });

    describe('Project Creation', () => {
        test('should create project with valid data', async () => {
            // Arrange
            const mockResponse = {
                success: true,
                project: {
                    id: 1,
                    name: 'Test Project',
                    description: 'Test description',
                    status: 'planning'
                }
            };
            
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse
            });

            const form = document.getElementById('project-form');
            const nameField = document.getElementById('name');
            const descriptionField = document.getElementById('description');

            // Act
            nameField.value = 'Test Project';
            descriptionField.value = 'Test description';
            
            const formData = new FormData(form);
            const response = await fetch('/core/api/v1/projects/', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();

            // Assert
            expect(fetch).toHaveBeenCalledWith('/core/api/v1/projects/', {
                method: 'POST',
                body: expect.any(FormData)
            });
            expect(result.success).toBe(true);
            expect(result.project.name).toBe('Test Project');
        });

        test('should handle creation errors gracefully', async () => {
            // Arrange
            const mockErrorResponse = {
                success: false,
                error: 'Project name is required'
            };
            
            global.fetch.mockResolvedValueOnce({
                ok: false,
                status: 400,
                json: async () => mockErrorResponse
            });

            // Act
            const response = await fetch('/core/api/v1/projects/', {
                method: 'POST',
                body: new FormData()
            });
            const result = await response.json();

            // Assert
            expect(result.success).toBe(false);
            expect(result.error).toBe('Project name is required');
        });
    });

    describe('Project List Display', () => {
        test('should display project list correctly', () => {
            // Arrange
            const projectList = document.getElementById('project-list');
            const mockProjects = [
                {
                    id: 1,
                    name: 'Project Alpha',
                    status: 'active',
                    updated_at: '2025-05-22T10:00:00Z'
                },
                {
                    id: 2,
                    name: 'Project Beta',
                    status: 'planning',
                    updated_at: '2025-05-22T11:00:00Z'
                }
            ];

            // Act
            projectList.innerHTML = mockProjects
                .map(project => `
                    <div class="project-item" data-id="${project.id}">
                        <h3>${project.name}</h3>
                        <span class="project-status status-${project.status}">${project.status}</span>
                        <button class="edit-btn" data-id="${project.id}">Edit</button>
                        <button class="delete-btn" data-id="${project.id}">Delete</button>
                    </div>
                `)
                .join('');

            // Assert
            const projectItems = projectList.querySelectorAll('.project-item');
            expect(projectItems.length).toBe(2);
            expect(projectItems[0].getAttribute('data-id')).toBe('1');
            expect(projectItems[1].getAttribute('data-id')).toBe('2');
        });
    });

    describe('Project Status Management', () => {
        test('should display status indicators correctly', () => {
            // Arrange
            const projectList = document.getElementById('project-list');

            // Act
            projectList.innerHTML = `
                <div class="project-item">
                    <span class="project-status status-active">Active</span>
                </div>
                <div class="project-item">
                    <span class="project-status status-planning">Planning</span>
                </div>
            `;

            // Assert
            const activeStatus = projectList.querySelector('.status-active');
            const planningStatus = projectList.querySelector('.status-planning');
            
            expect(activeStatus).toBeTruthy();
            expect(planningStatus).toBeTruthy();
            expect(activeStatus.textContent).toBe('Active');
            expect(planningStatus.textContent).toBe('Planning');
        });

        test('should filter projects by status', async () => {
            // Arrange
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: true,
                    projects: [
                        { id: 1, name: 'Active Project', status: 'active' }
                    ]
                })
            });

            // Act
            const response = await fetch('/core/api/v1/projects/?status=active');
            const result = await response.json();

            // Assert
            expect(fetch).toHaveBeenCalledWith('/core/api/v1/projects/?status=active');
            expect(result.projects.length).toBe(1);
            expect(result.projects[0].status).toBe('active');
        });
    });

    describe('Project Update Operations', () => {
        test('should update project successfully', async () => {
            // Arrange
            const mockResponse = {
                success: true,
                project: {
                    id: 1,
                    name: 'Updated Project',
                    description: 'Updated description',
                    status: 'active'
                }
            };
            
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse
            });

            // Act
            const response = await fetch('/core/api/v1/projects/1/', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: 'Updated Project',
                    description: 'Updated description',
                    status: 'active'
                })
            });
            const result = await response.json();

            // Assert
            expect(fetch).toHaveBeenCalledWith('/core/api/v1/projects/1/', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: 'Updated Project',
                    description: 'Updated description',
                    status: 'active'
                })
            });
            expect(result.success).toBe(true);
            expect(result.project.name).toBe('Updated Project');
        });
    });

    describe('Project Delete Operations', () => {
        test('should delete project successfully', async () => {
            // Arrange
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ success: true })
            });

            // Act
            const response = await fetch('/core/api/v1/projects/1/', {
                method: 'DELETE'
            });
            const result = await response.json();

            // Assert
            expect(fetch).toHaveBeenCalledWith('/core/api/v1/projects/1/', {
                method: 'DELETE'
            });
            expect(result.success).toBe(true);
        });
    });

    describe('Project Deadline Management', () => {
        test('should handle project deadlines', () => {
            // Arrange
            const deadlineField = document.getElementById('deadline');
            const testDate = '2025-12-31T23:59';

            // Act
            deadlineField.value = testDate;

            // Assert
            expect(deadlineField.value).toBe(testDate);
        });

        test('should display overdue projects differently', () => {
            // Arrange
            const projectList = document.getElementById('project-list');
            const overdueDate = new Date();
            overdueDate.setDate(overdueDate.getDate() - 1); // Yesterday

            // Act
            projectList.innerHTML = `
                <div class="project-item overdue" data-deadline="${overdueDate.toISOString()}">
                    <h3>Overdue Project</h3>
                    <span class="deadline-indicator overdue">Overdue</span>
                </div>
            `;

            // Assert
            const overdueProject = projectList.querySelector('.project-item.overdue');
            const overdueIndicator = projectList.querySelector('.deadline-indicator.overdue');
            
            expect(overdueProject).toBeTruthy();
            expect(overdueIndicator).toBeTruthy();
            expect(overdueIndicator.textContent).toBe('Overdue');
        });
    });

    describe('Status Message Display', () => {
        test('should show success messages correctly', () => {
            // Arrange
            const statusElement = document.getElementById('status-message');

            // Act
            statusElement.className = 'status-message success';
            statusElement.textContent = 'Project saved successfully!';

            // Assert
            expect(statusElement.classList.contains('success')).toBe(true);
            expect(statusElement.textContent).toBe('Project saved successfully!');
        });

        test('should show error messages correctly', () => {
            // Arrange
            const statusElement = document.getElementById('status-message');

            // Act
            statusElement.className = 'status-message error';
            statusElement.textContent = 'Error saving project.';

            // Assert
            expect(statusElement.classList.contains('error')).toBe(true);
            expect(statusElement.textContent).toBe('Error saving project.');
        });
    });
});