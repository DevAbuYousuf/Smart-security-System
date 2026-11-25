
const User = require("../models/User");

// ========================================
// CREATE ADMIN
// SUPER ADMIN ONLY
// ========================================
const createAdmin = async (req, res) => {
    try {
        const { name, email, password } = req.body;

        if (
            typeof name !== "string" ||
            typeof email !== "string" ||
            typeof password !== "string" ||
            !name.trim() ||
            !email.trim() ||
            !password
        ) {
            return res.status(400).json({
                success: false,
                message: "Name, email and password are required.",
            });
        }

        if (password.length < 12) {
            return res.status(400).json({
                success: false,
                message: "Password must be at least 12 characters.",
            });
        }

        const normalizedEmail = email.trim().toLowerCase();

        const existingUser = await User.findOne({
            email: normalizedEmail,
        });

        if (existingUser) {
            return res.status(409).json({
                success: false,
                message: "An account with this email already exists.",
            });
        }

        const admin = await User.create({
            name: name.trim(),
            email: normalizedEmail,
            password,
            role: "ADMIN",
        });

        return res.status(201).json({
            success: true,
            message: "Admin created successfully.",
            admin: {
                id: admin._id,
                name: admin.name,
                email: admin.email,
                role: admin.role,
                isActive: admin.isActive,
                createdAt: admin.createdAt,
            },
        });
    } catch (error) {
        if (error.code === 11000) {
            return res.status(409).json({
                success: false,
                message: "Email already exists.",
            });
        }

        console.error("Create Admin Error:", error.message);

        return res.status(500).json({
            success: false,
            message: "Failed to create Admin.",
        });
    }
};

// ========================================
// GET ALL ADMINS
// SUPER ADMIN ONLY
// ========================================
const getAllAdmins = async (req, res) => {
    try {
        const admins = await User.find({
            role: "ADMIN",
        })
            .select("-password")
            .sort({ createdAt: -1 });

        return res.status(200).json({
            success: true,
            count: admins.length,
            admins,
        });
    } catch (error) {
        console.error("Get Admins Error:", error.message);

        return res.status(500).json({
            success: false,
            message: "Failed to retrieve Admins.",
        });
    }
};

// ========================================
// UPDATE ADMIN STATUS
// SUPER ADMIN ONLY
// ========================================
const updateAdminStatus = async (req, res) => {
    try {
        const { isActive } = req.body;
        const { id } = req.params;

        if (typeof isActive !== "boolean") {
            return res.status(400).json({
                success: false,
                message: "isActive must be true or false.",
            });
        }

        const admin = await User.findOne({
            _id: id,
            role: "ADMIN",
        });

        if (!admin) {
            return res.status(404).json({
                success: false,
                message: "Admin account not found.",
            });
        }

        admin.isActive = isActive;
        await admin.save();

        return res.status(200).json({
            success: true,
            message: `Admin account ${isActive ? "activated" : "deactivated"} successfully.`,
            admin: {
                id: admin._id,
                name: admin.name,
                email: admin.email,
                role: admin.role,
                isActive: admin.isActive,
            },
        });
    } catch (error) {
        console.error("Update Admin Status Error:", error.message);

        return res.status(500).json({
            success: false,
            message: "Failed to update Admin status.",
        });
    }
};

module.exports = {
    createAdmin,
    getAllAdmins,
    updateAdminStatus,
};
