
const express = require("express");
const router = express.Router();

const {
    createPerson,
    getAllPersons,
    getPersonById,
    updatePerson,
    deactivatePerson
} = require("../controllers/personController");

// CREATE PERSON
router.post("/", createPerson);

// GET ALL PERSONS
router.get("/", getAllPersons);

// GET SINGLE PERSON
router.get("/:id", getPersonById);

// UPDATE PERSON
router.put("/:id", updatePerson);

// DEACTIVATE PERSON
router.patch("/:id/deactivate", deactivatePerson);

module.exports = router;
