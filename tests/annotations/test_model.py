from movak.annotations.model import AnnotationDocument, AnnotationTier, IntervalAnnotation, PointAnnotation
from movak.gui.controllers.annotation_editor_controller import AnnotationEditorController


def test_annotation_tier_keeps_annotations_sorted():
    tier = AnnotationTier(
        name="Words",
        tier_type="interval",
        annotations=[
            IntervalAnnotation(1.0, 2.0, "b"),
            IntervalAnnotation(0.2, 0.8, "a"),
        ],
    )

    assert [annotation.text for annotation in tier.annotations] == ["a", "b"]


def test_controller_can_split_and_merge_interval_annotations():
    document = AnnotationDocument(
        duration_seconds=5.0,
        tiers=[
            AnnotationTier(
                name="Words",
                tier_type="interval",
                annotations=[IntervalAnnotation(0.5, 2.5, "hello")],
            )
        ],
    )
    controller = AnnotationEditorController(document)
    tier = document.tiers[0]
    original_annotation = tier.annotations[0]

    controller.select_annotation(tier.id, original_annotation.id)
    split_annotation = controller.split_selected_interval_at_time(1.5)

    assert split_annotation is not None
    assert len(tier.annotations) == 2
    assert tier.annotations[0].end_time == 1.5
    assert tier.annotations[1].start_time == 1.5

    merged_annotation = controller.merge_selected_interval_with_next()

    assert merged_annotation is None
    controller.select_annotation(tier.id, tier.annotations[0].id)
    merged_annotation = controller.merge_selected_interval_with_next()
    assert merged_annotation is not None
    assert len(tier.annotations) == 1
    assert tier.annotations[0].start_time == 0.5
    assert tier.annotations[0].end_time == 2.5


def test_controller_clamps_interval_dragging_against_neighbors():
    document = AnnotationDocument(
        duration_seconds=5.0,
        tiers=[
            AnnotationTier(
                name="Phones",
                tier_type="interval",
                annotations=[
                    IntervalAnnotation(0.0, 1.0, "a"),
                    IntervalAnnotation(1.0, 2.0, "b"),
                    IntervalAnnotation(2.0, 3.0, "c"),
                ],
            )
        ],
    )
    controller = AnnotationEditorController(document)
    tier = document.tiers[0]
    middle_annotation = tier.annotations[1]

    assert controller.move_interval(tier.id, middle_annotation.id, 2.5, announce=False) is True
    assert middle_annotation.start_time == 1.0
    assert middle_annotation.end_time == 2.0

    assert controller.resize_interval_start(tier.id, middle_annotation.id, -1.0, announce=False) is True
    assert controller.resize_interval_end(tier.id, middle_annotation.id, 4.0, announce=False) is True
    assert middle_annotation.start_time == 1.0
    assert middle_annotation.end_time == 2.0


def test_controller_creates_point_annotations_at_cursor_time():
    document = AnnotationDocument(
        duration_seconds=5.0,
        tiers=[AnnotationTier(name="Events", tier_type="point", annotations=[])],
    )
    controller = AnnotationEditorController(document)
    tier = document.tiers[0]

    point_annotation = controller.create_point(tier.id, 1.75, text="burst")

    assert isinstance(point_annotation, PointAnnotation)
    assert point_annotation.time == 1.75
    assert tier.annotations[0].text == "burst"
