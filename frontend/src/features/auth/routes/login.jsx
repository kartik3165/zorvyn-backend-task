import LoginCard from "../components/LoginCard";

export default function LoginPage() {
    return (
        <div className="relative min-h-screen w-full bg-black overflow-hidden">
            {/* Background Image with 50% opacity */}
            <div
                className="absolute inset-0 z-0 bg-cover bg-center bg-no-repeat opacity-30 pointer-events-none"
                style={{
                    backgroundImage: 'url("/13149561_network_communications_background_with_flowing_cyber_dots_1609.jpg")'
                }}
            />

            {/* Login Content */}
            <LoginCard />
        </div>
    );
}