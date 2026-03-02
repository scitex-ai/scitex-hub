/**
 * Writer Sections Manager Module
 * Handles hierarchical document sections (Shared, Manuscript, Supplementary, Revision)
 */

import { StorageManager } from "@/utils/storage";

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/sections.ts loaded",
);
export interface Section {
  id: string;
  name: string;
  label: string;
  path?: string;
  category?: string;
  order?: number;
  visible?: boolean;
  content?: string;
  optional?: boolean;
  view_only?: boolean;
  instruction?: string;
  is_directory?: boolean;
}

export interface SectionCategory {
  label: string;
  description: string;
  sections: Section[];
  supports_crud?: boolean;
}

export interface SectionHierarchy {
  shared: SectionCategory;
  manuscript: SectionCategory;
  supplementary: SectionCategory;
  revision: SectionCategory;
}

export class SectionsManager {
  private sections: Map<string, Section> = new Map();
  private hierarchy: SectionHierarchy | null = null;
  private storage: StorageManager;
  private currentSection: string = "manuscript/compiled_pdf";
  private onSectionChangeCallback?: (section: string) => void;
  private onSectionsUpdateCallback?: (sections: Section[]) => void;
  private onHierarchyLoadCallback?: (hierarchy: SectionHierarchy) => void;

  constructor() {
    this.storage = new StorageManager("writer_sections_");
    this.initializeSections();
  }

  /**
   * Initialize sections - loads hierarchical structure from API
   */
  private async initializeSections(): Promise<void> {
    // Load hierarchy from API
    await this.loadHierarchy();

    // Load content from WRITER_CONFIG if available (from Django backend)
    const writerConfig = (window as any).WRITER_CONFIG;
    if (writerConfig?.sections) {
      let loadedCount = 0;
      Object.entries(writerConfig.sections).forEach(([sectionId, content]) => {
        // Find section in hierarchy and set content
        const section = this.sections.get(sectionId);
        if (section && content) {
          section.content = content as string;
          // Also save to storage for offline access
          this.storage.save(`content_${sectionId}`, content);
          loadedCount++;
        }
      });
      console.log(
        "[Sections] Loaded content from WRITER_CONFIG for",
        loadedCount,
        "sections",
      );
    }

    console.log("[Sections] Initialized with", this.sections.size, "sections");
  }

  /**
   * Load hierarchical section structure from API
   */
  async loadHierarchy(): Promise<void> {
    try {
      const response = await fetch("/writer/api/sections-config/");
      const data = await response.json();

      if (data.success && data.hierarchy) {
        this.hierarchy = data.hierarchy;

        // Populate sections map from hierarchy
        this.sections.clear();
        let order = 0;

        if (this.hierarchy) {
          Object.entries(this.hierarchy).forEach(([categoryKey, category]) => {
            const cat = category as SectionCategory;
            cat.sections.forEach((section: Section) => {
              const sectionWithDefaults: Section = {
                ...section,
                category: categoryKey,
                order: order++,
                visible: section.visible ?? true,
                content: section.content ?? "",
              };
              this.sections.set(section.id, sectionWithDefaults);
            });
          });
        }

        console.log(
          "[Sections] Loaded hierarchy with",
          this.sections.size,
          "sections",
        );

        if (this.onHierarchyLoadCallback && this.hierarchy) {
          this.onHierarchyLoadCallback(this.hierarchy);
        }
      }
    } catch (error) {
      console.error("[Sections] Failed to load hierarchy:", error);
      // Fall back to basic structure if API fails
      this.createFallbackStructure();
    }
  }

  /**
   * Create fallback structure if API fails
   */
  private createFallbackStructure(): void {
    const fallbackSections: Section[] = [
      {
        id: "manuscript/abstract",
        name: "abstract",
        label: "Abstract",
        category: "manuscript",
        order: 0,
        visible: true,
        content: "",
      },
      {
        id: "manuscript/introduction",
        name: "introduction",
        label: "Introduction",
        category: "manuscript",
        order: 1,
        visible: true,
        content: "",
      },
      {
        id: "manuscript/methods",
        name: "methods",
        label: "Methods",
        category: "manuscript",
        order: 2,
        visible: true,
        content: "",
      },
      {
        id: "manuscript/results",
        name: "results",
        label: "Results",
        category: "manuscript",
        order: 3,
        visible: true,
        content: "",
      },
      {
        id: "manuscript/discussion",
        name: "discussion",
        label: "Discussion",
        category: "manuscript",
        order: 4,
        visible: true,
        content: "",
      },
    ];

    fallbackSections.forEach((section) => {
      this.sections.set(section.id, section);
    });

    console.log("[Sections] Using fallback structure");
  }

  /**
   * Get all sections
   */
  getAll(): Section[] {
    return Array.from(this.sections.values()).sort(
      (a, b) => (a.order ?? 0) - (b.order ?? 0),
    );
  }

  /**
   * Get visible sections
   */
  getVisible(): Section[] {
    return this.getAll().filter((s) => s.visible);
  }

  /**
   * Get sections by category
   */
  getByCategory(category: string): Section[] {
    return this.getAll().filter((s) => s.category === category);
  }

  /**
   * Get hierarchy
   */
  getHierarchy(): SectionHierarchy | null {
    return this.hierarchy;
  }

  /**
   * Set callback for hierarchy load
   */
  onHierarchyLoad(callback: (hierarchy: SectionHierarchy) => void): void {
    this.onHierarchyLoadCallback = callback;
  }

  /**
   * Get section by id
   */
  get(id: string): Section | undefined {
    return this.sections.get(id);
  }

  /**
   * Add a new section
   */
  add(section: Section): void {
    this.sections.set(section.id, section);
    this.save();
    this.notifyUpdate();
    console.log("[Sections] Added section:", section.id);
  }

  /**
   * Update section
   */
  update(id: string, changes: Partial<Section>): void {
    const section = this.sections.get(id);
    if (section) {
      Object.assign(section, changes);
      this.save();
      this.notifyUpdate();
      console.log("[Sections] Updated section:", id);
    }
  }

  /**
   * Remove section
   */
  remove(id: string): void {
    if (this.sections.delete(id)) {
      this.save();
      this.notifyUpdate();
      console.log("[Sections] Removed section:", id);
    }
  }

  /**
   * Set section content
   */
  setContent(id: string, content: string): void {
    const section = this.sections.get(id);
    if (section) {
      section.content = content;
      this.storage.save(`content_${id}`, content);
    }
  }

  /**
   * Get section content
   */
  getContent(id: string): string {
    const section = this.sections.get(id);
    if (section && section.content) {
      return section.content;
    }

    // Try to load from storage
    const stored = this.storage.load<string>(`content_${id}`);
    if (stored) {
      return stored;
    }

    return "";
  }

  /**
   * Switch to section
   */
  switchTo(id: string): boolean {
    if (this.sections.has(id)) {
      this.currentSection = id;
      if (this.onSectionChangeCallback) {
        this.onSectionChangeCallback(id);
      }
      return true;
    }
    return false;
  }

  /**
   * Get current section
   */
  getCurrent(): string {
    return this.currentSection;
  }

  /**
   * Reorder sections
   */
  reorder(orderMap: Record<string, number>): void {
    Object.entries(orderMap).forEach(([id, order]) => {
      const section = this.sections.get(id);
      if (section) {
        section.order = order;
      }
    });
    this.save();
    this.notifyUpdate();
  }

  /**
   * Toggle section visibility
   */
  toggleVisibility(id: string): void {
    const section = this.sections.get(id);
    if (section) {
      section.visible = !section.visible;
      this.save();
      this.notifyUpdate();
    }
  }

  /**
   * Set callback for section changes
   */
  onSectionChange(callback: (section: string) => void): void {
    this.onSectionChangeCallback = callback;
  }

  /**
   * Set callback for sections update
   */
  onUpdate(callback: (sections: Section[]) => void): void {
    this.onSectionsUpdateCallback = callback;
  }

  /**
   * Notify listeners of update
   */
  private notifyUpdate(): void {
    if (this.onSectionsUpdateCallback) {
      this.onSectionsUpdateCallback(this.getAll());
    }
  }

  /**
   * Save sections to storage
   */
  private save(): void {
    this.storage.save("list", this.getAll());
  }

  /**
   * Export all sections as combined content
   */
  exportCombined(): string {
    return this.getVisible()
      .map((s) => `% ${s.label}\n${s.content ?? ""}`)
      .join("\n\n");
  }

  /**
   * Get total word count across all sections
   */
  getTotalWordCount(): number {
    return this.getAll().reduce((total, section) => {
      if (!section.content) return total;
      const words = section.content.trim().split(/\s+/).length;
      return total + words;
    }, 0);
  }
}
