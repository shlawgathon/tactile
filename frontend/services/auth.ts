export const login = async (email: string, password: string) => {
    return new Promise((resolve, reject) => {
        setTimeout(() => {
            if (email && password) {
                resolve({ email });
            } else {
                reject(new Error("Invalid credentials"));
            }
        }, 1000);
    });
};

export const logout = async () => {
    return new Promise((resolve) => {
        setTimeout(() => {
            resolve(true);
        }, 500);
    });
};
