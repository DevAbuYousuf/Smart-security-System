
const express = require("express");
const router = express.Router();

const {
    setupSuperAdmin,
    login,
} = require("../controllers/authController");

// First Super Admin setup
router.post("/setup/super-admin", setupSuperAdmin);

// Admin and Super Admin login
router.post("/login", login);

module.exports = router;
