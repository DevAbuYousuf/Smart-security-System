
const crypto = require("crypto");
const jwt = require("jsonwebtoken");
const User = require("../models/User");

// ========================================
// CREATE FIRST SUPER ADMIN
// ========================================
const setupSuperAdmin = async (req, res) => {
    try {
        const setupKey = req.get("x-setup-key");
        const expectedKey = process.env.SUPER_ADMIN_SETUP_KEY;

        if (!expectedKey) {
            return res.status(500).json({
                success: false,
                message: "Super Admin setup is not configured.",
            });
        }

        if (
            typeof setupKey !== "string" ||
            Buffer.byteLength(setupKey) !== Buffer.byteLength(expectedKey) ||
            !crypto.timingSafeEqual(
                Buffer.from(setupKey),
                Buffer.from(expectedKey)
            )
        ) {
            return res.status(401).json({
                success: false,
                message: "Invalid setup key.",
            });
        }

        const { name, email, password } = req.body;

        if (!name || !email || !password) {
            return res.status(400).json({
                success: false,
                message: "Name, email and password are required.",
            });
        }

        if (
            typeof name !== "string" ||
            typeof email !== "string" ||
            typeof password !== "string"
        ) {
            return res.status(400).json({
                success: false,
                message: "Invalid input format.",
            });
        }

        if (password.length < 12) {
            return res.status(400).json({
                success: false,
                message: "Password must be at least 12 characters.",
            });
        }

        const normalizedEmail = email.trim().toLowerCase();

        const existingSuperAdmin = await User.findOne({
            role: "SUPER_ADMIN",
        });

        if (existingSuperAdmin) {
            return res.status(409).json({
                success: false,
                message: "Super Admin has already been created.",
            });
        }

        const superAdmin = await User.create({
            name: name.trim(),
            email: normalizedEmail,
            password,
            role: "SUPER_ADMIN",
        });

        return res.status(201).json({
            success: true,
            message: "Super Admin created successfully.",
            user: {
                id: superAdmin._id,
                name: superAdmin.name,
                email: superAdmin.email,
                role: superAdmin.role,
            },
        });
    } catch (error) {
        if (error.code === 11000) {
            return res.status(409).json({
                success: false,
                message: "Super Admin or email already exists.",
            });
        }

        console.error("Super Admin setup error:", error.message);

        return res.status(500).json({
            success: false,
            message: "Failed to create Super Admin.",
        });
    }
};

// ========================================
// USER LOGIN
// ========================================
const login = async (req, res) => {
    try {
        const { email, password } = req.body;

        if (
            typeof email !== "string" ||
            typeof password !== "string" ||
            !email.trim() ||
            !password
        ) {
            return res.status(400).json({
                success: false,
                message: "Email and password are required.",
            });
        }

        if (!process.env.JWT_SECRET) {
            return res.status(500).json({
                success: false,
                message: "JWT authentication is not configured.",
            });
        }

        const user = await User.findOne({
            email: email.trim().toLowerCase(),
        }).select("+password");

        if (!user) {
            return res.status(401).json({
                success: false,
                message: "Invalid email or password.",
            });
        }

        if (!user.isActive) {
            return res.status(403).json({
                success: false,
                message: "Your account is inactive. Contact Super Admin.",
            });
        }

        const isPasswordValid = await user.comparePassword(password);

        if (!isPasswordValid) {
            return res.status(401).json({
                success: false,
                message: "Invalid email or password.",
            });
        }

        // Update last login
        user.lastLogin = new Date();
        await user.save();

        // Generate JWT
        const token = jwt.sign(
            {
                role: user.role,
            },
            process.env.JWT_SECRET,
            {
                subject: user._id.toString(),
                expiresIn: process.env.JWT_EXPIRES_IN || "1d",
            }
        );

        return res.status(200).json({
            success: true,
            message: "Login successful.",
            token,
            user: {
                id: user._id,
                name: user.name,
                email: user.email,
                role: user.role,
                lastLogin: user.lastLogin,
            },
        });
    } catch (error) {
        console.error("Login error:", error.message);

        return res.status(500).json({
            success: false,
            message: "Login failed. Please try again.",
        });
    }
};

module.exports = {
    setupSuperAdmin,
    login,
};
