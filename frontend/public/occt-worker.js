// Worker for processing STEP files using occt-import-js

self.onmessage = async (e) => {
    const { buffer } = e.data;

    try {
        // Load the WASM module
        // We use importScripts to load the JS wrapper from local public/occt-import-js.js
        importScripts('/occt-import-js.js');

        // @ts-ignore
        const occtimportjs = self.occtimportjs;

        const occt = await occtimportjs({
            locateFile: (name) => {
                if (name.endsWith('.wasm')) {
                    return '/occt-import-js.wasm';
                }
                return name;
            }
        });

        const fileContent = new Uint8Array(buffer);
        const result = occt.ReadStepFile(fileContent, null);

        if (!result || !result.meshes || result.meshes.length === 0) {
            throw new Error("No meshes found in STEP file");
        }

        // We can't send THREE objects back easily (circular refs, not structured cloneable), 
        // but we can send the raw mesh data which is what occt returns.
        // result.meshes contains { attributes: Float32Array, index: Uint16Array, color: [r,g,b] }

        // Simply post the message. Structured clone will handle TypedArrays.
        // We avoid manual transfer list for now to debug data missing issue.
        self.postMessage({ success: true, meshes: result.meshes });

    } catch (error) {
        self.postMessage({ success: false, error: error.message || String(error) });
    }
};
