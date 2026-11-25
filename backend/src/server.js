
const express = require("express");
const cors = require("cors");
const dotenv = require("dotenv");
const http = require("http");
const path = require("path");
const { Server } = require("socket.io");
const adminRoutes = require("./routes/adminRoutes");

const connectDB = require("./config/db");

const personRoutes = require("./routes/personRoutes");
const eventRoutes = require("./routes/eventRoutes");
const faceRoutes = require("./routes/faceRoutes");
const authRoutes = require("./routes/authRoutes");

dotenv.config();

const app = express();

// Create HTTP Server
const server = http.createServer(app);

// Initialize Socket.IO
const io = new Server(server, {
    cors: {
        origin: "*",
        methods: ["GET", "POST"],
    },
});

// Middleware
app.use(cors());
app.use(express.json());


// API Routes
app.use("/api/persons", personRoutes);
app.use("/api/events", eventRoutes);
app.use("/api/faces", faceRoutes);
app.use("/api/admins", adminRoutes);
app.use("/api/auth", authRoutes);

// Static Uploads
app.use(
    "/uploads",
    express.static(path.join(__dirname, "../uploads"))
);

// Make Socket.IO available in controllers
app.set("io", io);

// Socket.IO Connection
io.on("connection", (socket) => {
    console.log("Client connected:", socket.id);

    socket.emit("connection_success", {
        success: true,
        message: "Connected to Smart Security Server",
        socketId: socket.id,
    });

    socket.on("disconnect", () => {
        console.log("Client disconnected:", socket.id);
    });
});

// Home Route
app.get("/", (req, res) => {
    res.json({
        success: true,
        message: "Smart Security Backend is running",
        socketIO: "Enabled",
        authentication: "Enabled",
    });
});

// Server
const PORT = process.env.PORT || 5000;

const startServer = async () => {
    try {
        await connectDB();

        server.listen(PORT, () => {
            console.log(
                `Smart Security Server running on http://localhost:${PORT}`
            );
            console.log("Socket.IO is ready");
            console.log("Authentication routes are ready");
        });
    } catch (error) {
        console.error("Server startup failed:", error.message);
        process.exit(1);
    }
};

startServer();
