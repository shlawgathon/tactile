const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080/api';

export const getCurrentUser = async () => {
    try {
        const response = await fetch(`${API_URL}/users/me`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
        });

        if (!response.ok) {
            return null;
        }

        return await response.json();
    } catch (error) {
        console.error("Error fetching user:", error);
        return null;
    }
};

export const logout = async () => {
    try {
        await fetch(`${API_URL.replace('/api', '')}/logout`, {
            method: 'POST',
            credentials: 'include',
        });
        return true;
    } catch (error) {
        console.error("Logout error:", error);
        return false;
    }
};