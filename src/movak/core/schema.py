"""Annotation schema model."""

from __future__ import annotations

from dataclasses import dataclass, field

from movak.core.recording import Recording


@dataclass(slots=True)
class AnnotationSchema:
    """Definition of allowed annotation structures.

    Parameters
    ----------
    tier_order
        Ordered tier hierarchy from child to parent.
    labels
        Allowed labels grouped by tier.
    """

    tier_order: list[str] = field(default_factory=list)
    labels: dict[str, set[str]] = field(default_factory=dict)

    def validate_tier(self, tier_name: str) -> bool:
        """Check whether a tier is valid for the schema.

        Parameters
        ----------
        tier_name
            Tier name to validate.

        Returns
        -------
        bool
            Validation result.
        """
        return tier_name in self.tier_order

    def validate_label(self, tier_name: str, label: str) -> bool:
        """Check whether a label is valid for a tier.

        Parameters
        ----------
        tier_name
            Tier name to inspect.
        label
            Label value to validate.

        Returns
        -------
        bool
            Validation result.
        """
        allowed_labels = self.labels.get(tier_name)
        if allowed_labels is None:
            return True
        return label in allowed_labels

    def validate_recording(self, recording: Recording) -> None:
        """Validate tier membership and hierarchy for a recording.

        Parameters
        ----------
        recording
            Recording to validate.

        Raises
        ------
        ValueError
            Raised when tiers are missing or hierarchy constraints are violated.
        """
        self._validate_tiers_exist(recording)
        self._validate_parent_links(recording)
        self._validate_label_sets(recording)
        self._validate_hierarchy(recording)

    def _validate_tiers_exist(self, recording: Recording) -> None:
        for tier_name, tier in recording.tiers.items():
            if not self.validate_tier(tier_name):
                raise ValueError(
                    f"Tier '{tier_name}' is not defined in the annotation schema."
                )
            if tier.parent_tier is not None and tier.parent_tier not in recording.tiers:
                raise ValueError(
                    f"Parent tier '{tier.parent_tier}' for tier '{tier_name}' is missing."
                )

    def _validate_parent_links(self, recording: Recording) -> None:
        order_lookup = {tier_name: index for index, tier_name in enumerate(self.tier_order)}
        for tier_name, tier in recording.tiers.items():
            if tier.parent_tier is None:
                continue
            child_index = order_lookup[tier_name]
            parent_index = order_lookup[tier.parent_tier]
            if parent_index != child_index + 1:
                raise ValueError(
                    f"Tier '{tier_name}' must point to its immediate schema parent."
                )

    def _validate_label_sets(self, recording: Recording) -> None:
        for tier_name, tier in recording.tiers.items():
            for interval in tier.intervals:
                if not self.validate_label(tier_name, interval.label):
                    raise ValueError(
                        f"Label '{interval.label}' is not allowed on tier '{tier_name}'."
                    )

    def _validate_hierarchy(self, recording: Recording) -> None:
        for tier in recording.tiers.values():
            if tier.parent_tier is None:
                continue
            parent_intervals = recording.tiers[tier.parent_tier].intervals
            for interval in tier.intervals:
                if not any(
                    parent_interval.start <= interval.start
                    and interval.end <= parent_interval.end
                    for parent_interval in parent_intervals
                ):
                    raise ValueError(
                        f"Interval '{interval.token_id}' in tier '{tier.name}' is not "
                        "contained within a parent interval."
                    )
