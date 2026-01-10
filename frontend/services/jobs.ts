const API_URL = 'http://localhost:8080/api';

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

export const createJob = async (fileId: string, filename: string): Promise<Job | null> => {
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
                material: "PLA"
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
