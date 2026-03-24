"""Prompt builder — assemble generation prompts for each video segment."""

from __future__ import annotations

from infinite_dream.models.project import Project, VideoSegment


class PromptBuilder:
    """Build complete visual-generation prompts for video segments."""

    def build(self, segment: VideoSegment, project: Project) -> str:
        """Assemble a rich prompt for a single VideoSegment.

        Injects:
          [Style]        — style visual keywords
          [Character]    — appearance keywords for characters present
          [Environment]  — scene/environment keywords
          [Continue from]— previous segment end description (continuity)
          [Action]       — segment content / action description
          [Camera]       — camera motion / direction
        """
        parts: list[str] = []

        # ── Style ──
        if project.style:
            kw = ", ".join(project.style.visual_keywords)
            if kw:
                parts.append(f"[Style] {kw}")

        # ── Characters ──
        char_descs: list[str] = []
        for char_kw in segment.character_keywords:
            char_descs.append(char_kw)
        # Also look up by ID from project characters
        if project.characters and not char_descs:
            # Attempt to match characters via script segment
            for ch in project.characters:
                if _character_mentioned(ch.name, segment.visual_prompt):
                    kw_str = ", ".join(ch.appearance_keywords) if ch.appearance_keywords else ch.description
                    char_descs.append(f"{ch.name}: {kw_str}")
        if char_descs:
            parts.append(f"[Character] {'; '.join(char_descs)}")

        # ── Environment ──
        env_parts: list[str] = list(segment.environment_keywords)
        # If we have scenes, find the matching one
        if project.enhanced_script and project.scenes:
            for script_seg in project.enhanced_script.segments:
                if script_seg.id == segment.script_segment_id and script_seg.scene_id:
                    scene = project.get_scene(script_seg.scene_id)
                    if scene:
                        env_parts.extend(scene.environment_keywords)
                        if scene.time_of_day != "day":
                            env_parts.append(f"{scene.time_of_day} lighting")
                    break
        if env_parts:
            parts.append(f"[Environment] {', '.join(dict.fromkeys(env_parts))}")

        # ── Continue from (continuity) ──
        if segment.prev_segment_end_description:
            parts.append(f"[Continue from] {segment.prev_segment_end_description}")

        # ── Action / Content ──
        if segment.visual_prompt:
            parts.append(f"[Action] {segment.visual_prompt}")

        # ── Camera ──
        cam = segment.camera_motion or "static"
        if project.style and project.style.camera_motion:
            cam = project.style.camera_motion if cam == "static" else cam
        parts.append(f"[Camera] {cam}")

        return "\n".join(parts)

    def build_all(self, project: Project) -> None:
        """Build prompts for every segment in the project's segment plan.

        Updates each VideoSegment.visual_prompt in-place.
        """
        if not project.segment_plan:
            return

        for segment in project.segment_plan.segments:
            # Preserve original content as action seed before overwrite
            original_content = segment.visual_prompt
            prompt = self.build(segment, project)

            # If the build didn't include an [Action] line (because visual_prompt
            # was overwritten in a previous pass), inject the original content
            if "[Action]" not in prompt and original_content:
                prompt += f"\n[Action] {original_content}"

            segment.visual_prompt = prompt


def _character_mentioned(name: str, text: str) -> bool:
    """Check if a character name appears in text."""
    if not text or not name:
        return False
    return name.lower() in text.lower()
