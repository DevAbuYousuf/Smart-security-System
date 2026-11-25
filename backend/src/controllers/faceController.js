
const Person = require("../models/Person");

// GET ACTIVE PERSONS FOR FACE RECOGNITION
const getActiveFaceLabels = async (req, res) => {
    try {
        const persons = await Person.find({
            isActive: true
        }).select("name faceLabel");

        const labels = {};

        persons.forEach((person) => {
            labels[person.faceLabel] = person.name;
        });

        return res.status(200).json({
            success: true,
            message: "Active face labels fetched successfully.",
            count: persons.length,
            data: labels
        });

    } catch (error) {
        console.error("Face Sync Error:", error.message);

        return res.status(500).json({
            success: false,
            message: "Failed to fetch face labels.",
            error: error.message
        });
    }
};

module.exports = {
    getActiveFaceLabels
};
