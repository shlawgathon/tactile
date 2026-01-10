'use client';

import React, { useEffect, useState, useRef } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Stage, Center, Grid, GizmoHelper, GizmoViewport } from '@react-three/drei';
import * as THREE from 'three';

interface StepViewerProps {
    url: string;
}

export default function StepViewer({ url }: StepViewerProps) {
    const [meshes, setMeshes] = useState<THREE.Mesh[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const workerRef = useRef<Worker | null>(null);

    useEffect(() => {
        let mounted = true;

        const load = async () => {
            if (!url) return;
            try {
                setLoading(true);
                setError(null);
                setMeshes([]);

                console.log("StepViewer: Starting load for", url);

                // Terminate previous worker if any
                if (workerRef.current) {
                    workerRef.current.terminate();
                }

                // Initialize Worker
                const worker = new Worker('/occt-worker.js');
                workerRef.current = worker;

                worker.onmessage = (e) => {
                    if (!mounted) return;

                    const { success, meshes: meshData, error: workerError } = e.data;

                    if (!success) {
                        console.error("StepViewer: Worker error", workerError);
                        setError(workerError || 'Failed to process STEP file');
                        setLoading(false);
                        return;
                    }

                    console.log("StepViewer: Worker success. Meshes:", meshData.length);

                    // Convert raw data to Three.js meshes
                    const loadedMeshes: THREE.Mesh[] = [];

                    try {
                        for (let i = 0; i < meshData.length; i++) {
                            const mesh = meshData[i];

                            // Debug first mesh structure
                            if (i === 0) {
                                console.log("First mesh structure (full):", mesh);
                            }

                            const geometry = new THREE.BufferGeometry();

                            // OCCT 0.0.23+ Structure Handling
                            // Data usually comes as { attributes: { position: { array: [...] }, normal: { array: [...] } }, index: { array: [...] } }
                            const positionData = mesh.attributes?.position || mesh.attributes; // Fallback for older structure just in case
                            const positionArray = positionData?.array || positionData; // Handle nested .array or direct array

                            const normalData = mesh.attributes?.normal;
                            const normalArray = normalData?.array;

                            const indexData = mesh.index;
                            const indexArray = indexData?.array || indexData;

                            if (!positionArray || positionArray.length === 0) {
                                console.warn(`Mesh ${i} has no position data, skipping.`);
                                continue;
                            }

                            // Convert standard arrays or TypedArrays to BufferAttributes
                            const posBuffer = positionArray instanceof Float32Array ? positionArray : new Float32Array(positionArray);
                            geometry.setAttribute('position', new THREE.BufferAttribute(posBuffer, 3));

                            // Use provided normals if available
                            if (normalArray && normalArray.length > 0) {
                                const normBuffer = normalArray instanceof Float32Array ? normalArray : new Float32Array(normalArray);
                                geometry.setAttribute('normal', new THREE.BufferAttribute(normBuffer, 3));
                            } else {
                                geometry.computeVertexNormals();
                            }

                            if (indexArray && indexArray.length > 0) {
                                const idxBuffer = indexArray instanceof Uint16Array ? indexArray : new Uint16Array(indexArray);
                                geometry.setIndex(new THREE.BufferAttribute(idxBuffer, 1));
                            }

                            // Use MeshNormalMaterial for debugging
                            const material = new THREE.MeshNormalMaterial({
                                side: THREE.DoubleSide
                            });

                            const threeMesh = new THREE.Mesh(geometry, material);
                            loadedMeshes.push(threeMesh);
                        }

                        if (loadedMeshes.length === 0) {
                            console.warn("StepViewer: No valid meshes created from worker data.");
                        }

                        setMeshes(loadedMeshes);
                    } catch (err: any) {
                        console.error("StepViewer: Error creating meshes", err);
                        setError("Failed to create 3D objects");
                    } finally {
                        setLoading(false);
                    }
                };

                worker.onerror = (err) => {
                    console.error("StepViewer: Worker encountered an error", err);
                    if (mounted) {
                        setError('Worker encountered an error');
                        setLoading(false);
                    }
                };

                // Fetch the file
                console.log("StepViewer: Fetching file...");
                const response = await fetch(url, { credentials: 'include' });
                if (!response.ok) throw new Error('Failed to fetch file');
                const buffer = await response.arrayBuffer();
                console.log("StepViewer: File fetched, size:", buffer.byteLength);

                // Send to worker
                worker.postMessage({ buffer }, [buffer]);

            } catch (err: any) {
                console.error("StepViewer: Load error", err);
                if (mounted) {
                    setError(err.message || 'Failed to load STEP file');
                    setLoading(false);
                }
            }
        };

        load();

        return () => {
            mounted = false;
            if (workerRef.current) {
                workerRef.current.terminate();
            }
        };
    }, [url]);

    return (
        <div className="w-full h-full relative bg-zinc-900 overflow-hidden min-h-[500px]">
            {loading && (
                <div className="absolute inset-0 flex flex-col items-center justify-center text-white z-10 bg-zinc-900/90 gap-4 backdrop-blur-sm">
                    {/* Custom CSS loader or just a nice animated icon */}
                    <div className="relative w-12 h-12">
                        <div className="absolute inset-0 border-4 border-zinc-700 rounded-full"></div>
                        <div className="absolute inset-0 border-4 border-t-primary border-r-transparent border-b-transparent border-l-transparent rounded-full animate-spin"></div>
                    </div>
                    <div className="flex flex-col items-center gap-1">
                        <span className="font-medium tracking-wide text-sm">LOADING MODEL</span>
                        <span className="text-xs text-zinc-500">Parsing STEP geometry...</span>
                    </div>
                </div>
            )}

            {error ? (
                <div className="absolute inset-0 flex items-center justify-center text-red-400 p-4 text-center">
                    Error loading model: {error}
                </div>
            ) : (
                <Canvas shadows camera={{ position: [0, 0, 150], fov: 50 }}>
                    <color attach="background" args={['#27272a']} />
                    <OrbitControls makeDefault />

                    <Grid infiniteGrid fadeDistance={500} sectionColor="#4a4a4a" cellColor="#333333" />

                    <Stage environment="city" intensity={0.6} adjustCamera={true}>
                        <Center>
                            <group>
                                {meshes.map((mesh, i) => (
                                    <primitive key={i} object={mesh} />
                                ))}
                            </group>
                        </Center>
                    </Stage>

                    <GizmoHelper alignment="bottom-right" margin={[80, 80]}>
                        <GizmoViewport axisColors={['#9d4b4b', '#2f7f4f', '#3b5b9d']} labelColor="white" />
                    </GizmoHelper>
                </Canvas>
            )}
        </div>
    );
}
