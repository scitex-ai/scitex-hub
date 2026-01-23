/**
 * Selection Utilities
 * Helper functions for object selection and manipulation
 */

/**
 * Get objects at a specific point on the canvas
 */
export function getObjectsAtPoint(
    canvas: any,
    x: number,
    y: number
): any[] {
    const objects: any[] = [];
    const allObjects = canvas.getObjects();

    for (const obj of allObjects) {
        if (obj.selectable !== false && obj.containsPoint({ x, y })) {
            objects.push(obj);
        }
    }

    return objects;
}

/**
 * Get currently selected objects from canvas
 */
export function getSelectedObjects(canvas: any): any[] {
    const activeObject = canvas.getActiveObject();
    if (!activeObject) return [];

    // Check if it's a selection (multiple objects)
    if (activeObject.type === 'activeSelection') {
        return activeObject.getObjects();
    }

    return [activeObject];
}

/**
 * Select multiple objects on canvas
 */
export function selectObjects(canvas: any, objects: any[]): void {
    if (objects.length === 0) {
        canvas.discardActiveObject();
        return;
    }

    if (objects.length === 1) {
        canvas.setActiveObject(objects[0]);
    } else {
        const selection = new (window as any).fabric.ActiveSelection(objects, {
            canvas: canvas,
        });
        canvas.setActiveObject(selection);
    }
    canvas.requestRenderAll();
}

/**
 * Deselect all objects
 */
export function deselectAll(canvas: any): void {
    canvas.discardActiveObject();
    canvas.requestRenderAll();
}

/**
 * Get object name for display
 */
export function getObjectName(obj: any): string {
    if (obj.customName) return obj.customName;

    const typeNames: { [key: string]: string } = {
        'rect': 'Rectangle',
        'circle': 'Circle',
        'triangle': 'Triangle',
        'line': 'Line',
        'arrow': 'Arrow',
        'text': 'Text',
        'i-text': 'Text',
        'textbox': 'Textbox',
        'image': 'Image',
        'group': 'Group',
        'path': 'Path',
        'polygon': 'Polygon',
    };

    return typeNames[obj.type] || 'Object';
}

/**
 * Get icon HTML for object type
 */
export function getObjectIcon(obj: any): string {
    const icons: { [key: string]: string } = {
        'rect': '⬜',
        'circle': '⚪',
        'triangle': '🔺',
        'line': '➖',
        'arrow': '➡️',
        'text': '📝',
        'i-text': '📝',
        'textbox': '📝',
        'image': '🖼️',
        'group': '📦',
        'path': '✏️',
        'polygon': '⬡',
    };

    return icons[obj.type] || '📐';
}

/**
 * Check if object is a panel border or label
 */
export function isPanelElement(obj: any): boolean {
    return obj.isPanelBorder === true || obj.isPanelLabel === true;
}

/**
 * Filter out panel elements from selection
 */
export function filterPanelElements(objects: any[]): any[] {
    return objects.filter(obj => !isPanelElement(obj));
}

/**
 * Sort objects by z-index (canvas order)
 */
export function sortByZIndex(canvas: any, objects: any[]): any[] {
    const allObjects = canvas.getObjects();
    return objects.sort((a, b) => {
        return allObjects.indexOf(a) - allObjects.indexOf(b);
    });
}
