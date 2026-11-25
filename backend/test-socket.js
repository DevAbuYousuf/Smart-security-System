
const { io } = require("socket.io-client");

const socket = io("http://localhost:5000");

socket.on("connect", () => {
    console.log("Connected to Smart Security Server!");
    console.log("Socket ID:", socket.id);
});

socket.on("connection_success", (data) => {
    console.log("Server Response:", data.message);
});

// Listen for security alerts
socket.on("security_alert", (alert) => {
    console.log("\n========== SECURITY ALERT ==========");
    console.log("Message:", alert.message);
    console.log("Event Type:", alert.data.eventType);
    console.log("Person:", alert.data.personName);
    console.log("Status:", alert.data.status);
    console.log("Camera:", alert.data.cameraId);
    console.log("Snapshot:", alert.data.snapshot);
    console.log("====================================\n");
});

socket.on("disconnect", () => {
    console.log("Disconnected from server.");
});

socket.on("connect_error", (error) => {
    console.log("Connection Error:", error.message);
});
