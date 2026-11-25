
const mongoose = require("mongoose");
const SecurityEvent = require("../models/SecurityEvent");

// ==========================================
// ESCAPE SPECIAL REGEX CHARACTERS
// ==========================================

const escapeRegex = (value) => {
    return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
};

// ==========================================
// GET ALL EVENTS + SEARCH + FILTER + PAGINATION
// ==========================================

const getAllEvents = async (req, res) => {
    try {
        const {
            eventType,
            startDate,
            endDate,
            search,
            personName,
            trackId,
            page = 1,
            limit = 10
        } = req.query;

        const currentPage = Number(page);
        const pageSize = Number(limit);

        // 1. Validate pagination

        if (
            !Number.isInteger(currentPage) ||
            !Number.isInteger(pageSize) ||
            currentPage < 1 ||
            pageSize < 1 ||
            pageSize > 100
        ) {
            return res.status(400).json({
                success: false,
                message: "Invalid page or limit. Limit must be between 1 and 100."
            });
        }

        const filter = {};

        // 2. Filter by event type

        const allowedEventTypes = [
            "ENTRY",
            "EXIT",
            "UNKNOWN_PERSON",
            "AUTHORIZED_PERSON"
        ];

        if (eventType) {
            const normalizedType = eventType.toUpperCase();

            if (!allowedEventTypes.includes(normalizedType)) {
                return res.status(400).json({
                    success: false,
                    message: "Invalid event type."
                });
            }

            filter.eventType = normalizedType;
        }

        // 3. Filter by event date

        const isValidDate = (date) => {
            if (
                typeof date !== "string" ||
                !/^\d{4}-\d{2}-\d{2}$/.test(date)
            ) {
                return false;
            }

            const parsed = new Date(`${date}T00:00:00.000Z`);

            return (
                !Number.isNaN(parsed.getTime()) &&
                parsed.toISOString().slice(0, 10) === date
            );
        };

        if (startDate || endDate) {
            if (
                (startDate && !isValidDate(startDate)) ||
                (endDate && !isValidDate(endDate))
            ) {
                return res.status(400).json({
                    success: false,
                    message: "Invalid date. Use YYYY-MM-DD format."
                });
            }

            if (startDate && endDate && startDate > endDate) {
                return res.status(400).json({
                    success: false,
                    message: "startDate cannot be after endDate."
                });
            }

            const dateFilter = {};

            if (startDate) {
                dateFilter.$gte = new Date(
                    `${startDate}T00:00:00.000Z`
                );
            }

            if (endDate) {
                const endExclusive = new Date(
                    `${endDate}T00:00:00.000Z`
                );

                endExclusive.setUTCDate(
                    endExclusive.getUTCDate() + 1
                );

                dateFilter.$lt = endExclusive;
            }

            filter.eventDate = dateFilter;
        }

        // 4. Search by person name
        // Supports both search and personName parameters

        const nameSearch = search ?? personName;

        if (nameSearch !== undefined) {
            if (typeof nameSearch !== "string") {
                return res.status(400).json({
                    success: false,
                    message: "Person name search must be text."
                });
            }

            const trimmedName = nameSearch.trim();

            if (trimmedName.length > 100) {
                return res.status(400).json({
                    success: false,
                    message: "Search text cannot exceed 100 characters."
                });
            }

            if (trimmedName) {
                const safeName = escapeRegex(trimmedName);

                filter.personName = {
                    $regex: safeName,
                    $options: "i"
                };
            }
        }

        // 5. Search by Track ID

        if (trackId !== undefined && trackId !== "") {
            const parsedTrackId = Number(trackId);

            if (
                !Number.isInteger(parsedTrackId) ||
                parsedTrackId < 0
            ) {
                return res.status(400).json({
                    success: false,
                    message: "Track ID must be a valid non-negative integer."
                });
            }

            filter.trackId = parsedTrackId;
        }

        // 6. Pagination

        const skip = (currentPage - 1) * pageSize;

        const events = await SecurityEvent.find(filter)
            .populate("person", "name role")
            .sort({ eventDate: -1, createdAt: -1 })
            .skip(skip)
            .limit(pageSize);

        const totalEvents = await SecurityEvent.countDocuments(filter);

        const totalPages = Math.ceil(totalEvents / pageSize);

        return res.status(200).json({
            success: true,
            message: "Events fetched successfully",
            pagination: {
                totalEvents,
                currentPage,
                pageSize,
                totalPages,
                hasNextPage: currentPage < totalPages,
                hasPreviousPage: currentPage > 1
            },
            count: events.length,
            data: events
        });

    } catch (error) {
        console.error("Get Events Error:", error.message);

        return res.status(500).json({
            success: false,
            message: "Failed to fetch events",
            error: error.message
        });
    }
};

// ==========================================
// GET SINGLE EVENT BY ID
// ==========================================

const getEventById = async (req, res) => {
    try {
        const { id } = req.params;

        if (!mongoose.Types.ObjectId.isValid(id)) {
            return res.status(400).json({
                success: false,
                message: "Invalid event ID."
            });
        }

        const event = await SecurityEvent.findById(id)
            .populate("person", "name role");

        if (!event) {
            return res.status(404).json({
                success: false,
                message: "Event not found."
            });
        }

        return res.status(200).json({
            success: true,
            message: "Event fetched successfully",
            data: event
        });

    } catch (error) {
        console.error("Get Single Event Error:", error.message);

        return res.status(500).json({
            success: false,
            message: "Failed to fetch event",
            error: error.message
        });
    }
};

// ==========================================
// CREATE SECURITY EVENT + SOCKET NOTIFICATION
// ==========================================

const createEvent = async (req, res) => {
    try {
        const {
            eventType,
            person,
            personName,
            status,
            confidence,
            snapshot,
            cameraId,
            trackId
        } = req.body;

        const event = await SecurityEvent.create({
            eventType,
            person: person || null,
            personName: personName || "Unknown Person",
            status,
            confidence,
            snapshot: req.file
                ? `/uploads/snapshots/${req.file.filename}`
                : (snapshot || null),
            cameraId: cameraId || "CAMERA_01",
            trackId: trackId ?? null
        });

        // Populate person details

        await event.populate("person", "name role");

        // Notify only for security alerts

        const shouldNotify =
            event.eventType === "UNKNOWN_PERSON" ||
            event.status === "UNAUTHORIZED";

        if (shouldNotify) {
            const io = req.app.get("io");

            if (io) {
                io.emit("security_alert", {
                    success: true,
                    message: "Security Alert!",
                    data: event
                });

                console.log(
                    "Security notification emitted:",
                    event.eventType,
                    event.personName
                );
            }
        }

        return res.status(201).json({
            success: true,
            message: "Security event saved",
            data: event
        });

    } catch (error) {
        console.error("Create Event Error:", error.message);

        return res.status(500).json({
            success: false,
            message: error.message
        });
    }
};

// ==========================================
// EXPORT CONTROLLERS
// ==========================================

module.exports = {
    createEvent,
    getAllEvents,
    getEventById
};
