
const express = require("express");
const router = express.Router();

const {
    createEvent,
    getAllEvents,
    getEventById
} = require("../controllers/eventController");

const upload = require("../middleware/upload");

// Create event with optional snapshot upload
router.post("/", upload.single("snapshot"), createEvent);

// Get all events with filters and pagination
router.get("/", getAllEvents);

// Get single event by MongoDB ID
router.get("/:id", getEventById);

module.exports = router;
