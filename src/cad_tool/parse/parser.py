import cadquery as cq
import logging

logger = logging.getLogger(__name__)

def parse_step(file_path: str) -> cq.Workplane:
    """
    Parses a STEP file using CadQuery.
    """
    logger.info(f"Parsing STEP file at {file_path}")
    try:
        return cq.importers.importStep(file_path)
    except Exception as e:
        logger.error(f"Error parsing STEP file: {e}")
        raise
