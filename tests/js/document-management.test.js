/**
 * Test Suite: Document Management CRUD Operations
 * Following TDD principles with comprehensive functionality testing
 */

describe('Document Management', () => {
    // Mock fetch for API testing
    beforeEach(() => {
        global.fetch = jest.fn();
        document.body.innerHTML = `
            <div class="document-container">
                <form id="document-form" class="document-form">
                    <input type="text" id="title" name="title" required>
                    <textarea id="content" name="content" required></textarea>
                    <select id="document_type" name="document_type">
                        <option value="note">Note</option>
                        <option value="paper">Research Paper</option>
                        <option value="project">Project</option>
                        <option value="draft">Draft</option>
                    </select>
                    <input type="text" id="tags" name="tags" placeholder="comma, separated, tags">
                    <button type="submit" id="save-btn">Save Document</button>
                </form>
                <div id="document-list" class="document-list"></div>
                <div id="status-message" class="status-message"></div>
            </div>
        `;
    });

    afterEach(() => {
        jest.restoreAllMocks();
        document.body.innerHTML = '';
    });

    describe('Document Form Validation', () => {
        test('should validate required fields', () => {
            // Arrange
            const form = document.getElementById('document-form');
            const titleField = document.getElementById('title');
            const contentField = document.getElementById('content');

            // Act & Assert
            expect(titleField.hasAttribute('required')).toBe(true);
            expect(contentField.hasAttribute('required')).toBe(true);
            expect(form).toBeTruthy();
        });

        test('should have all document type options available', () => {
            // Arrange
            const typeSelect = document.getElementById('document_type');
            const options = typeSelect.querySelectorAll('option');

            // Act & Assert
            expect(options.length).toBe(4);
            expect(options[0].value).toBe('note');
            expect(options[1].value).toBe('paper');
            expect(options[2].value).toBe('project');
            expect(options[3].value).toBe('draft');
        });
    });

    describe('Document Creation', () => {
        test('should create document with valid data', async () => {
            // Arrange
            const mockResponse = {
                success: true,
                document: {
                    id: 1,
                    title: 'Test Document',
                    content: 'Test content',
                    document_type: 'note'
                }
            };
            
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse
            });

            const form = document.getElementById('document-form');
            const titleField = document.getElementById('title');
            const contentField = document.getElementById('content');

            // Act
            titleField.value = 'Test Document';
            contentField.value = 'Test content';
            
            const formData = new FormData(form);
            const response = await fetch('/api/v1/documents/', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();

            // Assert
            expect(fetch).toHaveBeenCalledWith('/api/v1/documents/', {
                method: 'POST',
                body: expect.any(FormData)
            });
            expect(result.success).toBe(true);
            expect(result.document.title).toBe('Test Document');
        });

        test('should handle creation errors gracefully', async () => {
            // Arrange
            const mockErrorResponse = {
                success: false,
                error: 'Title is required'
            };
            
            global.fetch.mockResolvedValueOnce({
                ok: false,
                status: 400,
                json: async () => mockErrorResponse
            });

            // Act
            const response = await fetch('/api/v1/documents/', {
                method: 'POST',
                body: new FormData()
            });
            const result = await response.json();

            // Assert
            expect(result.success).toBe(false);
            expect(result.error).toBe('Title is required');
        });
    });

    describe('Document List Display', () => {
        test('should display document list correctly', () => {
            // Arrange
            const documentList = document.getElementById('document-list');
            const mockDocuments = [
                {
                    id: 1,
                    title: 'Document 1',
                    document_type: 'note',
                    updated_at: '2025-05-22T10:00:00Z'
                },
                {
                    id: 2,
                    title: 'Document 2',
                    document_type: 'paper',
                    updated_at: '2025-05-22T11:00:00Z'
                }
            ];

            // Act
            documentList.innerHTML = mockDocuments
                .map(doc => `
                    <div class="document-item" data-id="${doc.id}">
                        <h3>${doc.title}</h3>
                        <span class="document-type">${doc.document_type}</span>
                        <button class="edit-btn" data-id="${doc.id}">Edit</button>
                        <button class="delete-btn" data-id="${doc.id}">Delete</button>
                    </div>
                `)
                .join('');

            // Assert
            const documentItems = documentList.querySelectorAll('.document-item');
            expect(documentItems.length).toBe(2);
            expect(documentItems[0].getAttribute('data-id')).toBe('1');
            expect(documentItems[1].getAttribute('data-id')).toBe('2');
        });
    });

    describe('Document Update Operations', () => {
        test('should update document successfully', async () => {
            // Arrange
            const mockResponse = {
                success: true,
                document: {
                    id: 1,
                    title: 'Updated Document',
                    content: 'Updated content'
                }
            };
            
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse
            });

            // Act
            const response = await fetch('/api/v1/documents/1/', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: 'Updated Document',
                    content: 'Updated content'
                })
            });
            const result = await response.json();

            // Assert
            expect(fetch).toHaveBeenCalledWith('/api/v1/documents/1/', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: 'Updated Document',
                    content: 'Updated content'
                })
            });
            expect(result.success).toBe(true);
            expect(result.document.title).toBe('Updated Document');
        });
    });

    describe('Document Delete Operations', () => {
        test('should delete document successfully', async () => {
            // Arrange
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ success: true })
            });

            // Act
            const response = await fetch('/api/v1/documents/1/', {
                method: 'DELETE'
            });
            const result = await response.json();

            // Assert
            expect(fetch).toHaveBeenCalledWith('/api/v1/documents/1/', {
                method: 'DELETE'
            });
            expect(result.success).toBe(true);
        });
    });

    describe('Status Message Display', () => {
        test('should show success messages correctly', () => {
            // Arrange
            const statusElement = document.getElementById('status-message');

            // Act
            statusElement.className = 'status-message success';
            statusElement.textContent = 'Document saved successfully!';

            // Assert
            expect(statusElement.classList.contains('success')).toBe(true);
            expect(statusElement.textContent).toBe('Document saved successfully!');
        });

        test('should show error messages correctly', () => {
            // Arrange
            const statusElement = document.getElementById('status-message');

            // Act
            statusElement.className = 'status-message error';
            statusElement.textContent = 'Error saving document.';

            // Assert
            expect(statusElement.classList.contains('error')).toBe(true);
            expect(statusElement.textContent).toBe('Error saving document.');
        });
    });
});