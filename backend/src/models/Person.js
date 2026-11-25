const mongoose = require("mongoose");

const personSchema = new mongoose.Schema(
    {
        name: {
            type: String,
            required: true,
            trim: true,
        },

        faceLabel: {
            type: Number,
            required: true,
        },

        photo: {
            type: String,
            default: null,
        },

        role: {
            type: String,
            enum: ["OWNER", "FAMILY", "EMPLOYEE", "OTHER"],
            default: "OTHER",
        },

        isActive: {
            type: Boolean,
            default: true,
        },
    },
    {
        timestamps: true,
    }
);

module.exports = mongoose.model("Person", personSchema);