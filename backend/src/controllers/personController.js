
const mongoose = require("mongoose");
const Person = require("../models/Person");

// CREATE NEW PERSON
const createPerson = async (req, res) => {
    try {
        const {
            name,
            faceLabel,
            role,
            photo
        } = req.body;

        if (!name || faceLabel === undefined || faceLabel === "") {
            return res.status(400).json({
                success: false,
                message: "Name and faceLabel are required."
            });
        }

        const parsedFaceLabel = Number(faceLabel);

        if (
            !Number.isInteger(parsedFaceLabel) ||
            parsedFaceLabel < 0
        ) {
            return res.status(400).json({
                success: false,
                message: "faceLabel must be a non-negative integer."
            });
        }

        const existingPerson = await Person.findOne({
            faceLabel: parsedFaceLabel
        });

        if (existingPerson) {
            return res.status(409).json({
                success: false,
                message: "This faceLabel is already registered."
            });
        }

        const person = await Person.create({
            name,
            faceLabel: parsedFaceLabel,
            role: role || "OTHER",
            photo: photo || null
        });

        return res.status(201).json({
            success: true,
            message: "Person registered successfully.",
            data: person
        });

    } catch (error) {
        console.error("Create Person Error:", error.message);

        return res.status(500).json({
            success: false,
            message: "Failed to register person.",
            error: error.message
        });
    }
};


// GET ALL PERSONS
const getAllPersons = async (req, res) => {
    try {
        const {
            page = 1,
            limit = 10,
            search,
            isActive
        } = req.query;

        const currentPage = Number(page);
        const pageSize = Number(limit);

        if (
            !Number.isInteger(currentPage) ||
            !Number.isInteger(pageSize) ||
            currentPage < 1 ||
            pageSize < 1 ||
            pageSize > 100
        ) {
            return res.status(400).json({
                success: false,
                message: "Invalid page or limit."
            });
        }

        const filter = {};

        if (search) {
            filter.name = {
                $regex: search,
                $options: "i"
            };
        }

        if (isActive !== undefined) {
            if (!["true", "false"].includes(isActive)) {
                return res.status(400).json({
                    success: false,
                    message: "isActive must be true or false."
                });
            }

            filter.isActive = isActive === "true";
        }

        const skip = (currentPage - 1) * pageSize;

        const persons = await Person.find(filter)
            .sort({ createdAt: -1 })
            .skip(skip)
            .limit(pageSize);

        const totalPersons = await Person.countDocuments(filter);

        const totalPages = Math.ceil(totalPersons / pageSize);

        return res.status(200).json({
            success: true,
            message: "Persons fetched successfully.",
            pagination: {
                totalPersons,
                currentPage,
                pageSize,
                totalPages,
                hasNextPage: currentPage < totalPages,
                hasPreviousPage: currentPage > 1
            },
            count: persons.length,
            data: persons
        });

    } catch (error) {
        console.error("Get Persons Error:", error.message);

        return res.status(500).json({
            success: false,
            message: "Failed to fetch persons.",
            error: error.message
        });
    }
};


// GET SINGLE PERSON
const getPersonById = async (req, res) => {
    try {
        const { id } = req.params;

        if (!mongoose.Types.ObjectId.isValid(id)) {
            return res.status(400).json({
                success: false,
                message: "Invalid person ID."
            });
        }

        const person = await Person.findById(id);

        if (!person) {
            return res.status(404).json({
                success: false,
                message: "Person not found."
            });
        }

        return res.status(200).json({
            success: true,
            message: "Person fetched successfully.",
            data: person
        });

    } catch (error) {
        console.error("Get Person Error:", error.message);

        return res.status(500).json({
            success: false,
            message: "Failed to fetch person.",
            error: error.message
        });
    }
};


// UPDATE PERSON
const updatePerson = async (req, res) => {
    try {
        const { id } = req.params;
        const { name, faceLabel, role, photo, isActive } = req.body;

        if (!mongoose.Types.ObjectId.isValid(id)) {
            return res.status(400).json({
                success: false,
                message: "Invalid person ID."
            });
        }

        const person = await Person.findById(id);

        if (!person) {
            return res.status(404).json({
                success: false,
                message: "Person not found."
            });
        }

        if (faceLabel !== undefined) {
            const parsedFaceLabel = Number(faceLabel);

            if (
                !Number.isInteger(parsedFaceLabel) ||
                parsedFaceLabel < 0
            ) {
                return res.status(400).json({
                    success: false,
                    message: "faceLabel must be a non-negative integer."
                });
            }

            const duplicateLabel = await Person.findOne({
                faceLabel: parsedFaceLabel,
                _id: { $ne: id }
            });

            if (duplicateLabel) {
                return res.status(409).json({
                    success: false,
                    message: "This faceLabel is already in use."
                });
            }

            person.faceLabel = parsedFaceLabel;
        }

        if (name !== undefined) person.name = name;
        if (role !== undefined) person.role = role;
        if (photo !== undefined) person.photo = photo;

        if (isActive !== undefined) {
        if (typeof isActive !== "boolean") {
        return res.status(400).json({
            success: false,
            message: "isActive must be a boolean."
        });
    }

    person.isActive = isActive;
}

        await person.save();

        return res.status(200).json({
            success: true,
            message: "Person updated successfully.",
            data: person
        });

    } catch (error) {
        console.error("Update Person Error:", error.message);

        return res.status(500).json({
            success: false,
            message: "Failed to update person.",
            error: error.message
        });
    }
};


// DEACTIVATE PERSON
const deactivatePerson = async (req, res) => {
    try {
        const { id } = req.params;

        if (!mongoose.Types.ObjectId.isValid(id)) {
            return res.status(400).json({
                success: false,
                message: "Invalid person ID."
            });
        }

        const person = await Person.findById(id);

        if (!person) {
            return res.status(404).json({
                success: false,
                message: "Person not found."
            });
        }

        person.isActive = false;
        await person.save();

        return res.status(200).json({
            success: true,
            message: "Person deactivated successfully.",
            data: person
        });

    } catch (error) {
        console.error("Deactivate Person Error:", error.message);

        return res.status(500).json({
            success: false,
            message: "Failed to deactivate person.",
            error: error.message
        });
    }
};


module.exports = {
    createPerson,
    getAllPersons,
    getPersonById,
    updatePerson,
    deactivatePerson
};
