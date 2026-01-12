const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080/api';

export interface Job {
    id: string;
    originalFilename: string;
    status: string;
    createdAt: string;
    manufacturingProcess: string;
    progressPercent: number;
    fileStorageId: string;
}

export const getFileUrl = (fileId: string) => {
    return `${API_URL}/files/${fileId}`;
};

export const uploadFile = async (file: File): Promise<string | null> => {
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch(`${API_URL}/files`, {
            method: 'POST',
            body: formData,
            credentials: 'include', // Important for Auth
        });

        if (!response.ok) {
            console.error("Upload failed", await response.text());
            return null;
        }

        const data = await response.json();
        return data.fileId;
    } catch (error) {
        console.error("Error uploading file:", error);
        return null;
    }
};

export const createJob = async (fileId: string, filename: string, x402Budget?: number): Promise<Job | null> => {
    try {
        const response = await fetch(`${API_URL}/jobs`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                fileStorageId: fileId,
                originalFilename: filename,
                // Defaulting to FDM_3D_PRINTING for now as per MVP plan
                manufacturingProcess: "FDM_3D_PRINTING",
                material: "PLA",
                x402Budget: x402Budget ?? 1.0,
            }),
            credentials: 'include',
        });

        if (!response.ok) {
            console.error("Create job failed", await response.text());
            return null;
        }

        return await response.json();
    } catch (error) {
        console.error("Error creating job:", error);
        return null;
    }
};

export const getJob = async (id: string): Promise<Job | null> => {
    try {
        const response = await fetch(`${API_URL}/jobs/${id}`, {
            method: 'GET',
            credentials: 'include',
        });

        if (!response.ok) {
            return null;
        }

        return await response.json();
    } catch (error) {
        console.error("Error fetching job:", error);
        return null;
    }
};

export const getJobs = async (): Promise<Job[]> => {
    try {
        const response = await fetch(`${API_URL}/jobs?sort=createdAt,desc`, {
            method: 'GET',
            credentials: 'include',
        });

        if (!response.ok) {
            return [];
        }

        const data = await response.json();
        return data.content || [];
    } catch (error) {
        console.error("Error fetching jobs:", error);
        return [];
    }
};

export interface AgentEvent {
    id: string;
    jobId: string;
    type: string;
    title: string;
    content: string;
    metadata: Record<string, any>;
    createdAt: string;
}

export const getJobEvents = async (jobId: string): Promise<AgentEvent[]> => {
    try {
        const response = await fetch(`${API_URL}/jobs/${jobId}/events`, {
            method: 'GET',
            credentials: 'include',
        });

        if (!response.ok) {
            return [];
        }

        return await response.json();
    } catch (error) {
        console.error("Error fetching job events:", error);
        return [];
    }
};

export interface QueryResponse {
    answer: string;
    sourcesUsed: number;
}

/**
 * Query the job's memory using RAG-based chat.
 * This allows users to ask questions about their CAD model analysis.
 */
export const queryJobMemory = async (jobId: string, query: string): Promise<QueryResponse | null> => {
    try {
        const response = await fetch(`${API_URL}/jobs/${jobId}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query }),
            credentials: 'include',
        });

        if (!response.ok) {
            console.error("Query failed", await response.text());
            return null;
        }

        return await response.json();
    } catch (error) {
        console.error("Error querying job memory:", error);
        return null;
    }
};

/**
 * Delete a job by ID.
 */
export const deleteJob = async (jobId: string): Promise<boolean> => {
    try {
        const response = await fetch(`${API_URL}/jobs/${jobId}`, {
            method: 'DELETE',
            credentials: 'include',
        });

        return response.ok;
    } catch (error) {
        console.error("Error deleting job:", error);
        return false;
    }
};

export interface AnalysisResult {
    id: string;
    jobId: string;
    markdownReport: string;
    c1UiReport: string;
    volume?: number;
    surfaceArea?: number;
    createdAt: string;
}

/**
 * Get the analysis results for a job, including the Thesys C1 UI report.
 */
export const getJobAnalysisResults = async (jobId: string): Promise<AnalysisResult | null> => {
    try {
        const response = await fetch(`${API_URL}/jobs/${jobId}/results`, {
            method: 'GET',
            credentials: 'include',
        });

        if (!response.ok) {
            return null;
        }

        return await response.json();
    } catch (error) {
        console.error("Error fetching job analysis results:", error);
        return null;
    }
};
