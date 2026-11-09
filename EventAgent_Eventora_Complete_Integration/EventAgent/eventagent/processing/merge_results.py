# Fields that should NEVER be overwritten
PROTECTED_FIELDS = {
    "url",
    "platform",
    "source_account",
    "query",
    "content_type",
}


def better_text(new_value, old_value):
    """
    Prefer longer, more descriptive text.
    Example:
    'Phoenix' -> 'Phoenix Marketcity, Velachery'
    """

    if not old_value:
        return new_value

    new_value = str(new_value).strip()
    old_value = str(old_value).strip()

    if len(new_value) > len(old_value):
        return new_value

    return old_value


def merge_events(original, enriched):
    """
    Merge enriched event information into the original event.

    Rules:
    - Never overwrite original discovery metadata.
    - Fill only missing fields.
    - Prefer richer venue/organizer names.
    - Keep highest confidence.
    - Preserve original event identity.
    """

    merged = original.copy()

    for key, value in enriched.items():

        # Skip empty values
        if value is None:
            continue

        if not str(value).strip():
            continue

        # Never overwrite original discovery information
        if key in PROTECTED_FIELDS:
            continue

        # New field
        if key not in merged:
            merged[key] = value
            continue

        # Empty original value
        if merged[key] is None or not str(merged[key]).strip():
            merged[key] = value
            continue

        # Prefer longer venue names
        if key == "venue":
            merged[key] = better_text(value, merged[key])
            continue

        # Prefer longer organizer names
        if key == "organizer":
            merged[key] = better_text(value, merged[key])
            continue

        # Keep highest confidence
        if key == "confidence":
            merged[key] = max(
                merged.get("confidence", 0),
                value
            )
            continue

        # Fill category only if missing
        if key == "category":

            if not merged.get("category"):
                merged["category"] = value

            continue

        # Fill city only if missing
        if key == "city":

            if not merged.get("city"):
                merged["city"] = value

            continue

        # Fill date only if missing
        if key == "date":

            if not merged.get("date"):
                merged["date"] = value

            continue

        # Fill time only if missing
        if key == "time":

            if not merged.get("time"):
                merged["time"] = value

            continue

        # Everything else:
        # Keep original value

    return merged