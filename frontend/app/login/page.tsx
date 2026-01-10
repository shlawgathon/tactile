"use client";
import { faGithub } from "@fortawesome/free-brands-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Instrument_Sans } from "next/font/google";

const instrument_sans = Instrument_Sans({
    weight: ["400", "500", "600"],
    subsets: ["latin"],
});

const Login = () => {
    return (
        <div className='w-full h-screen flex flex-col items-center justify-center text-black bg-white bg-[radial-gradient(#2b2b2b_1px,transparent_1px)] [background-size:35px_35px]'>
            <h1 className={`border border-white mb-2 bg-primary text-white py-1 px-5 text-2xl font-extrabold ${instrument_sans.className}`}>tacticle3d</h1>
            <p className="bg-white px-1">sign in below (we'll fix your designs😉)</p>
            <button
                onClick={() => window.location.href = "http://localhost:8080/oauth2/authorization/github"}
                className="mt-3 cursor-pointer px-4 py-2 flex flex-row items-center gap-2 bg-white text-black border border-black hover:bg-black hover:text-white duration-200 transition-colors"
            >
                <FontAwesomeIcon icon={faGithub} />
                Continue with GitHub
            </button>
        </div >
    );
}

export default Login;