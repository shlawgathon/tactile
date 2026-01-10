"use client";
import { useState } from "react";
import { login } from "../../services/auth";
import toast from "react-hot-toast";
import router from "next/router";
import { Instrument_Sans } from "next/font/google";

const instrument_sans = Instrument_Sans({
    weight: ["400", "500", "600"],
    subsets: ["latin"],
});

const Login = () => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');

    const handleLogin = async () => {
        if (!email || !password) {
            toast.error('You must fill all of the fields');
            return;
        }

        toast.promise(
            login(email, password),
            {
                loading: 'Logging in...',
                success: <b>Success</b>,
                error: <b>Invalid Credentials</b>,
            }
        ).then((user) => {
            if (user) {
                router.push('/');
            }
        });
    }

    return (
        <div className='w-full h-screen flex flex-row items-center justify-center text-black bg-white bg-[radial-gradient(#2b2b2b_1px,transparent_1px)] [background-size:35px_35px]'>
            <div className='w-full md:w-1/2 flex flex-col h-screen p-10 justify-between'>
                <div className="flex w-full">
                    <h1 className={`bg-black text-white py-1 px-5 text-2xl font-extrabold ${instrument_sans.className}`}>tacticle</h1>
                </div>

                <div className='flex flex-col justify-self-center bg-white'>
                    <p className={`font-extrabold text-4xl ${instrument_sans.className}`}>Welcome Back!</p>
                    <p className='text-zinc-400 font-regular text-sm mb-5'>Login to your account</p>

                    <input value={email} onChange={(e) => setEmail(e.target.value)}
                        className='mt-3 bg-foreground px-4 py-3 outline-none border text-sm' placeholder='Enter your email'
                        type="email" />
                    <input value={password} onChange={(e) => setPassword(e.target.value)}
                        className='mt-3 bg-foreground px-4 py-3 outline-none border text-sm' placeholder='Create a password'
                        type="password" />

                    <button onClick={handleLogin} className="w-full bg-black hover:bg-zinc-700 text-white mt-5 py-2 font-bold hover:cursor-pointer duration-200 transition-colors">
                        Login
                    </button>

                    <a className='justify-start text-zinc-400 font-sm pt-1 w-max mt-1' href="/register">Don't have a account yet?</a>
                </div>

                <div className='flex flex-col w-max'>
                    <p className='text-zinc-400 font-regular text-sm bg-white'>© 2026 Tactile. All Rights Reserved.</p>
                </div>
            </div>

            <div className='hidden md:block w-1/2 h-screen'>
            </div>
        </div>
    );
}

export default Login;