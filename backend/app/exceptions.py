class ClaimNotFoundError(Exception):
    """Raised when a claim_id does not exist. Routers translate this to a 404."""

    def __init__(self, claim_id: str):
        self.claim_id = claim_id
        super().__init__(f"Claim '{claim_id}' was not found")


class EvidenceNotFoundError(Exception):
    """Raised when an evidence id does not exist. Routers translate this to a 404."""

    def __init__(self, evidence_id: str):
        self.evidence_id = evidence_id
        super().__init__(f"Evidence '{evidence_id}' was not found")


class UnsupportedFileTypeError(Exception):
    """Raised when an uploaded file isn't one of the accepted image formats. -> 415."""

    def __init__(self, content_type: str):
        self.content_type = content_type
        super().__init__(f"Unsupported file type '{content_type}'. Only JPEG, PNG, and WEBP images are allowed.")


class FileTooLargeError(Exception):
    """Raised when an uploaded file exceeds the per-image size limit. -> 413."""

    def __init__(self, max_size_mb: int):
        self.max_size_mb = max_size_mb
        super().__init__(f"File exceeds the maximum size of {max_size_mb}MB.")


class EvidenceLimitExceededError(Exception):
    """Raised when a claim already has the maximum number of evidence images. -> 409."""

    def __init__(self, max_images: int):
        self.max_images = max_images
        super().__init__(f"A claim can have at most {max_images} evidence images.")


class InvalidImageError(Exception):
    """Raised when a file has an accepted content-type/extension but isn't a decodable image. -> 400."""

    def __init__(self):
        super().__init__("The uploaded file is not a valid image.")
