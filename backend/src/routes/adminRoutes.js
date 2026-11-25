
const express = require("express");
const router = express.Router();

const {
    createAdmin,
    getAllAdmins,
    updateAdminStatus,
} = require("../controllers/adminController");

const {
    protect,
    authorize,
} = require("../middleware/authMiddleware");

// Every Admin Management route requires Super Admin access
router.use(protect, authorize("SUPER_ADMIN"));

router.post("/", createAdmin);

router.get("/", getAllAdmins);

router.patch("/:id/status", updateAdminStatus);

module.exports = router;
