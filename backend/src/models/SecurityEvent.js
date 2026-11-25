
const mongoose = require("mongoose");

const securityEventSchema = new mongoose.Schema(
    {
        eventType: {
            type: String,
            enum: [
                "ENTRY",
                "EXIT",
                "UNKNOWN_PERSON",
                "AUTHORIZED_PERSON"
            ],
            required: true,
        },

        person: {
            type: mongoose.Schema.Types.ObjectId,
            ref: "Person",
            default: null,
        },

        personName: {
            type: String,
            default: "Unknown Person",
        },

       status: {
    type: String,
    enum: ["AUTHORIZED", "UNAUTHORIZED", "UNVERIFIED"],
    required: true,
},

        confidence: {
            type: Number,
            default: null,
        },

        snapshot: {
            type: String,
            default: null,
        },

        cameraId: {
            type: String,
            default: "CAMERA_01",
        },
        trackId: {
            type: Number,
             default: null,
        },

        eventDate: {
            type: Date,
            default: Date.now,
        },
    },
    {
        timestamps: true,
    }
);

module.exports = mongoose.model(
    "SecurityEvent",
    securityEventSchema
);
