"""Entry point for the project."""

import sys
from argparse import Namespace
from typing import Any, Dict, List

from hledger_config.arg_parser import (
    assert_args_are_valid,
    create_arg_parser,
)
from hledger_config.config.load_config import Config, load_config
from hledger_core.generics.enums import ClassifierType, LogicType
from hledger_core.TransactionObjects.Receipt import Receipt
from hledger_receipt_processing.reading_history.load_receipts_from_dir import (
    load_receipts_from_dir,
)
from typeguard import typechecked

from hledger_preprocessor.checks.check_categorisation import (
    check_categorisation,
)
from hledger_preprocessor.checks.check_matching import check_matching

# get_models uses try/except ImportError internally for optional hledger-ai
from hledger_preprocessor.get_models import get_models
from hledger_preprocessor.management.helper import edit_receipt
from hledger_preprocessor.management.main_manager import (
    manage_batch_match_receipts,
    manage_creating_new_setup,
    manage_creating_receipt_img_labels_with_tui,
    manage_generating_rules,
    manage_match_csv_to_csv,
    manage_matching_manual_receipt_objs_to_account_transactions,
    manage_preprocessing_assets,
    manage_preprocessing_csvs,
)


@typechecked
def main() -> None:
    # Parse input arguments
    parser = create_arg_parser()

    # NEW
    args: Namespace = parser.parse_args()
    assert_args_are_valid(args=args)

    # --run-pipeline: full pipeline (replaces start.sh).
    if args.run_pipeline:
        if not args.config:
            print("Error: --config is required for --run-pipeline.")
            sys.exit(1)
        from hledger_preprocessor.pipeline import run_pipeline

        run_pipeline(
            config_path=args.config,
            randomize=args.randomize,
            non_interactive=args.non_interactive,
        )
        return

    # --map-csv runs before anything else: it only needs the config path,
    # not a fully loaded Config (the CSV may not be in config yet).
    if args.map_csv:
        from hledger_csv_mapping.csv_mapping.mapping_tui import (
            run_csv_mapping_tui,
        )

        run_csv_mapping_tui(
            csv_filepath=args.map_csv,
            config_path=args.config,
        )
        return  # mapping done — exit

    config: Config = load_config(
        config_path=args.config,
        pre_processed_output_dir=args.pre_processed_output_dir,
    )

    labelled_receipts: List[Receipt] = load_receipts_from_dir(config=config)

    # --- Pre-flight checks (US-4.6 and US-4.7) ---
    if args.check_categorisation:
        models_for_check: Dict[ClassifierType, Dict[LogicType, Any]] = (
            get_models(quick_categorisation=True)
        )
        errors = check_categorisation(
            config=config,
            models=models_for_check,
            labelled_receipts=labelled_receipts,
        )
        if errors:
            print("")
            print("=" * 60)
            print(f"  {len(errors)} uncategorised transaction(s) found")
            print("=" * 60)
            for err in errors:
                print(str(err))
            print("=" * 60)
            sys.exit(1)
        else:
            print("All CSV transactions can be categorised.")

    if args.check_matching:
        check_matching(
            config=config,
            labelled_receipts=labelled_receipts,
        )

    # If only checks were requested, exit now.
    if args.check_categorisation or args.check_matching:
        if not any(
            [
                args.preprocess_csvs,
                args.preprocess_assets,
                args.link_receipts_to_transactions,
                getattr(args, "match_receipts", False),
                getattr(args, "match_csv_to_csv", False),
                getattr(args, "match_transactions", False),
                args.edit_receipt,
                args.new_setup,
                args.generate_rules,
                args.tui_label_receipts,
            ]
        ):
            return

    # --match-transactions expands into both matching sub-flags.
    if args.match_transactions:
        args.match_receipts = True
        args.match_csv_to_csv = True

    if (
        args.preprocess_csvs
        or args.preprocess_assets
        or args.link_receipts_to_transactions
        or args.match_receipts
        or args.match_csv_to_csv
    ):
        models: Dict[ClassifierType, Dict[LogicType, Any]] = get_models(
            quick_categorisation=args.quick_categorisation
        )

        # Batch-match receipts to CSV transactions BEFORE preprocessing,
        # so that withdrawal metadata is available when bank CSVs are
        # processed.
        if args.match_receipts:
            labelled_receipts = manage_batch_match_receipts(
                config=config,
                labelled_receipts=labelled_receipts,
            )

        # Reconcile linked-account CSV transactions (interactive for
        # cross-currency matches).  The suppress_ids and category_overrides
        # are passed to preprocess_generic_csvs so it doesn't re-run
        # reconciliation.
        suppress_ids: Dict = {}
        category_overrides: Dict[str, str] = {}
        if args.match_csv_to_csv:
            suppress_ids, category_overrides = manage_match_csv_to_csv(
                config=config,
                labelled_receipts=labelled_receipts,
            )

        if args.preprocess_csvs:
            manage_preprocessing_csvs(
                config=config,
                models=models,
                labelled_receipts=labelled_receipts,
                suppress_ids=suppress_ids if suppress_ids else None,
                category_overrides=(
                    category_overrides if category_overrides else None
                ),
            )

        if args.preprocess_assets:
            manage_preprocessing_assets(
                config=config,
                models=models,
                labelled_receipts=labelled_receipts,
            )

        if args.link_receipts_to_transactions:
            manage_matching_manual_receipt_objs_to_account_transactions(
                config=config,
                models=models,
                labelled_receipts=labelled_receipts,
            )

    if args.edit_receipt:
        edit_receipt(config=config, labelled_receipts=labelled_receipts)

    if args.new_setup:
        manage_creating_new_setup(
            config=config,
            labelled_receipts=labelled_receipts,
        )

    if args.generate_rules:
        manage_generating_rules(
            config=config,
        )

    if args.train_models:
        try:
            from hledger_ai.training.train_runner import run_training

            results = run_training(
                labelled_receipts=labelled_receipts,
                models_dir=(
                    config.ai.models_dir
                    if config.ai
                    else "~/.hledger-ai/models"
                ),
                feedback_dir=(
                    config.ai.feedback_dir
                    if config.ai
                    else "~/.hledger-ai/feedback"
                ),
                model_choice=args.model,
                force_retrain=args.force_retrain,
                ai_config=config.ai,
            )
            for model_name, result in results.items():
                if result.get("trained"):
                    print(
                        f"  {model_name}: trained"
                        f" ({result.get('num_examples', '?')} examples)"
                    )
                elif result.get("skipped"):
                    print(f"  {model_name}: skipped ({result.get('reason')})")
                else:
                    print(
                        f"  {model_name}:"
                        f" {result.get('error', 'unknown error')}"
                    )
        except ImportError:
            print(
                "Error: hledger-ai is not installed. "
                "Install it to use --train-models."
            )
            sys.exit(1)

    if args.make_ai_labels:
        try:
            from hledger_ai.auto_labeller import AutoLabeller
            from hledger_ai.get_models import build_extraction_pipeline

            ai_cfg = config.ai
            pipeline = build_extraction_pipeline(
                ollama_url=(
                    ai_cfg.ollama_url if ai_cfg else "http://localhost:11434"
                ),
                vlm_model=ai_cfg.vlm_model if ai_cfg else "qwen3-vl:2b",
                text_model=ai_cfg.text_model if ai_cfg else "qwen3:0.6b",
            )
            labeller = AutoLabeller(
                pipeline=pipeline,
                auto_accept_threshold=(
                    ai_cfg.auto_accept_threshold if ai_cfg else 0.9
                ),
            )

            from hledger_preprocessor.helper import get_images_in_folder

            image_dir = config.dir_paths.get_path(
                "receipt_images_input_dir", absolute=True
            )
            label_dir = config.dir_paths.get_path(
                "receipt_labels_dir", absolute=True
            )
            images = get_images_in_folder(folder_path=image_dir)
            if not images:
                print("No receipt images found to label.")
            else:
                result = labeller.label_batch(
                    image_paths=images, output_dir=label_dir
                )
                print(
                    f"AI labelling complete: {result['labelled']} labelled,"
                    f" {result['skipped']} skipped,"
                    f" {result['failed']} failed"
                    f" (out of {result['total']} images)"
                )
        except ImportError:
            print(
                "Error: hledger-ai is not installed. "
                "Install it to use --make-ai-labels."
            )
            sys.exit(1)

    if args.group_receipts and not args.tui_label_receipts:
        # Standalone grouping: rotate, crop, then group only (no labelling).
        from hledger_core.helper import get_images_in_folder
        from hledger_receipt_processing.receipts_to_objects.edit_images.crop_image import (  # noqa: E501
            crop_images,
        )
        from hledger_receipt_processing.receipts_to_objects.edit_images.rotate_all_images import (  # noqa: E501
            rotate_images,
        )
        from hledger_receipt_processing.receipts_to_objects.group_images import (  # noqa: E501
            group_receipt_images,
            load_image_grouping,
            save_image_grouping,
        )

        raw_imgs = get_images_in_folder(
            folder_path=config.dir_paths.get_path(
                "receipt_images_input_dir", absolute=True
            )
        )
        rotate_images(raw_receipt_img_filepaths=raw_imgs, config=config)
        crop_images(raw_receipt_img_filepaths=raw_imgs, config=config)

        if args.regroup:
            group_receipt_images(config=config, image_paths=raw_imgs)
        else:
            saved = load_image_grouping(config=config)
            if saved is not None:
                grouped_paths: set = {p for group in saved for p in group}
                new_images = [fp for fp in raw_imgs if fp not in grouped_paths]
                if new_images:
                    print(
                        f"\n{len(new_images)} new image(s) to group"
                        f" ({len(saved)} existing groups kept)."
                    )
                    new_groups = group_receipt_images(
                        config=config, image_paths=new_images
                    )
                    # Merge: saved groups + newly grouped images.
                    # group_receipt_images already saved its own result;
                    # overwrite with the merged version.
                    merged = saved + new_groups
                    save_image_grouping(config=config, groups=merged)
                    print(f"Merged grouping: {len(merged)} total groups.")
                else:
                    print(
                        "Loaded existing grouping"
                        f" ({len(saved)} groups). "
                        "No new images. Use --regroup to redo."
                    )
            else:
                group_receipt_images(config=config, image_paths=raw_imgs)

    if args.tui_label_receipts:
        if args.skip_ai:
            config._skip_ai = True
        if args.group_receipts:
            config._group_receipts = True
        if args.regroup:
            config._regroup = True
        manage_creating_receipt_img_labels_with_tui(
            config=config, labelled_receipts=labelled_receipts, verbose=False
        )


if __name__ == "__main__":
    main()
