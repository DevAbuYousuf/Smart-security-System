
const express = require("express");
const router = express.Router();

const {
    getActiveFaceLabels
} = require("../controllers/faceController");

router.get("/labels", getActiveFaceLabels);

module.exports = router;
