/**
 * API Client Utility Module
 * Provides reusable fetch wrapper with CSRF token handling
 */

import { getCsrfToken } from "./csrf.js";

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/static/ts/utils/api.ts loaded",
);
export interface ApiRequestInit extends Omit<RequestInit, "body"> {
  body?: BodyInit | object | null;
}

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

/**
 * API Client class for making requests with automatic CSRF token handling
 */
export class ApiClient {
  private baseUrl: string;
  private csrfTokenFn: () => string;

  constructor(baseUrl: string = "", csrfTokenFn: () => string = getCsrfToken) {
    this.baseUrl = baseUrl;
    this.csrfTokenFn = csrfTokenFn;
  }

  /**
   * Prepare request headers with CSRF token
   */
  private getHeaders(headers?: HeadersInit): HeadersInit {
    const defaultHeaders: HeadersInit = {
      "Content-Type": "application/json",
      "X-CSRFToken": this.csrfTokenFn(),
    };

    return { ...defaultHeaders, ...headers };
  }

  /**
   * Make GET request
   */
  async get<T = any>(
    url: string,
    options?: ApiRequestInit,
  ): Promise<ApiResponse<T>> {
    return this.request<T>(url, { ...options, method: "GET" });
  }

  /**
   * Make POST request
   */
  async post<T = any>(
    url: string,
    body?: any,
    options?: ApiRequestInit,
  ): Promise<ApiResponse<T>> {
    return this.request<T>(url, {
      ...options,
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  /**
   * Make PUT request
   */
  async put<T = any>(
    url: string,
    body?: any,
    options?: ApiRequestInit,
  ): Promise<ApiResponse<T>> {
    return this.request<T>(url, {
      ...options,
      method: "PUT",
      body: JSON.stringify(body),
    });
  }

  /**
   * Make PATCH request
   */
  async patch<T = any>(
    url: string,
    body?: any,
    options?: ApiRequestInit,
  ): Promise<ApiResponse<T>> {
    return this.request<T>(url, {
      ...options,
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  /**
   * Make DELETE request
   */
  async delete<T = any>(
    url: string,
    options?: ApiRequestInit,
  ): Promise<ApiResponse<T>> {
    return this.request<T>(url, { ...options, method: "DELETE" });
  }

  /**
   * Core request method
   */
  private async request<T = any>(
    url: string,
    options: ApiRequestInit = {},
  ): Promise<ApiResponse<T>> {
    const fullUrl = this.baseUrl ? `${this.baseUrl}${url}` : url;

    try {
      // Build request with proper body handling
      const requestInit: any = {
        ...options,
        headers: this.getHeaders(options.headers),
      };

      // Ensure body is properly stringified if it's an object
      if (
        options.body &&
        typeof options.body === "object" &&
        !(options.body instanceof FormData)
      ) {
        requestInit.body = JSON.stringify(options.body);
      }

      const response = await fetch(fullUrl, requestInit);

      // Handle different response types
      const contentType = response.headers.get("content-type");
      let data: any;

      if (contentType?.includes("application/json")) {
        data = await response.json();
      } else {
        data = await response.text();
      }

      if (!response.ok) {
        console.error(`[API] Error ${response.status}: ${url}`, data);
        return {
          success: false,
          error: data?.error || data?.message || `HTTP ${response.status}`,
          data: data as T,
        };
      }

      return {
        success: true,
        data: data as T,
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      console.error(`[API] Request failed: ${url}`, error);
      return {
        success: false,
        error: message,
      };
    }
  }
}

// Export singleton instance
export const apiClient = new ApiClient();
