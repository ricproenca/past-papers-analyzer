# Vision for diagram pages - is documented but not implemented — it needs a larger architectural lift

Pages flagged has_image: True only get a text hint. 
Claude never sees the actual visual. For diagram-based questions the visuals array is populated by inference, not observation.
Requires multimodal calls with image blocks from page.to_image(), restructuring pdf_reader.py to return image bytes, and a separate prompt strategy for visual pages. 
Worth a dedicated phase.