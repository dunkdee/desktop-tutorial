#!/usr/bin/env python3
"""
CLI runner for the movie generator pipeline.

Usage:
  python run.py --prompt "A detective story set in 1920s Chicago" \
                --title "Shadows of the Windy City" \
                --privacy private

  python run.py --script-only --prompt "..." --title "..."
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))


def main():
    parser = argparse.ArgumentParser(description="Movie Generator — Claude Fable 5 + Higgins → YouTube")
    parser.add_argument("--prompt", required=True, help="Film premise / concept")
    parser.add_argument("--title", required=True, help="Film title")
    parser.add_argument("--description", default="", help="YouTube description override")
    parser.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    parser.add_argument("--script-only", action="store_true", help="Generate script only, skip video + upload")
    parser.add_argument("--no-upload", action="store_true", help="Generate video but skip YouTube upload")
    args = parser.parse_args()

    if args.script_only:
        from script_generator import generate_script, generate_title_and_description
        print(f"\n=== Generating script for '{args.title}' ===\n")
        script = generate_script(args.prompt, args.title)
        print(script)
        print("\n=== YouTube Metadata ===\n")
        import json
        meta = generate_title_and_description(script, args.title)
        print(json.dumps(meta, indent=2))
        return

    from pipeline import run_pipeline
    print(f"\n=== Starting full pipeline for '{args.title}' ===\n")
    result = run_pipeline(
        prompt=args.prompt,
        title=args.title,
        description=args.description,
        privacy=args.privacy,
        upload=not args.no_upload,
    )

    print(f"\n=== Pipeline complete: {result.status} ===")
    print(f"Scenes generated : {result.scene_count}")
    if result.youtube_url:
        print(f"YouTube URL      : {result.youtube_url}")
    if result.errors:
        print(f"Errors           : {result.errors}")


if __name__ == "__main__":
    main()
