import json
import os
import re
from datetime import datetime
import argparse
from typing import List, Dict
from dotenv import load_dotenv
from itertools import batched
from smolagents.agents import ToolCallingAgent
from smolagents.models import HfApiModel, OpenAIServerModel
from smolagents import DuckDuckGoSearchTool

load_dotenv()


class KindleToObsidianAgent:
    def __init__(
        self,
        highlights_file: str,
        output_dir: str,
        model_name: str = "gpt-4o-mini",
        openai_api_key: str = os.getenv("OPENAI_API_KEY"),
    ):
        """Initialize the agent with the path to highlights file and output directory."""
        self.highlights_file = highlights_file
        self.output_dir = output_dir
        self.model_name = model_name
        self.openai_api_key = openai_api_key

        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Load highlights
        with open(highlights_file, "r", encoding="utf-8") as f:
            self.book_data = json.load(f)

        # Setup search tool
        self.search_tool = DuckDuckGoSearchTool()

        # Define custom tools
        self.tools = [self.search_tool]

        # Initialize model based on type
        if "gpt" in model_name.lower():
            # Using OpenAI model
            if not openai_api_key:
                raise ValueError("OpenAI API key is required for OpenAI models")

            self.model = OpenAIServerModel(model_id=model_name, api_key=openai_api_key)
        else:
            # Using HuggingFace model
            self.model = HfApiModel(model_id=model_name)

        # Initialize agent with tools
        self.agent = ToolCallingAgent(
            model=self.model,
            tools=self.tools,
            max_steps=5,
            name="Kindle to Obsidian Agent",
            description="Generates kindle highlights in obsidian format",
        )

    def extract_key_concepts(
        self, title: str, author: str, highlights: List[str]
    ) -> List[Dict[str, str]]:
        """Extract key concepts from the book highlights."""
        highlights_text = "\n\n".join(highlights)
        prompt = f"""
        Analyze these highlights from the book "{title}" by {author}. 
        Identify 5-10 key concepts or ideas presented in the text.
        For each concept, provide a brief description based on the highlights.
        
        HIGHLIGHTS:
        {highlights_text}
        
        Return your answer as a list of concepts with descriptions.
        """

        response = self.agent.run(prompt)

        # Parse response into structured concepts
        concepts = []
        # Basic parsing - in a real implementation, you'd want more robust parsing
        concept_pattern = r"(?:^|\n)(?:- |•\s*|[0-9]+\.\s*)([^:]+):\s*(.+?)(?=\n(?:- |•\s*|[0-9]+\.\s*)|$)"
        matches = re.finditer(concept_pattern, response, re.MULTILINE | re.DOTALL)

        for match in matches:
            concepts.append(
                {"name": match.group(1).strip(), "description": match.group(2).strip()}
            )

        return concepts

    def enrich_concepts(self, concepts: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Enrich concepts with additional information from the web if needed."""
        enriched_concepts = []

        for concept in concepts:
            prompt = f"""
            Do we need additional information about the concept: "{concept['name']}" 
            with description: "{concept['description']}"?
            
            Answer with YES or NO first, then explain why.
            """

            decision = self.agent.run(prompt)

            if "YES" in decision.upper():
                # Ask the agent to search for and integrate information
                integration_prompt = f"""
                I need more information about this concept:
                Name: {concept['name']}
                Description: {concept['description']}
                
                Please search for more information about this concept using the search tool,
                and then create an improved description that integrates any new information 
                while maintaining relevance to the original concept.
                """

                improved_description = self.agent.run(integration_prompt)
                concept["description"] = improved_description.strip()

            enriched_concepts.append(concept)

        return enriched_concepts

    def generate_summary(
        self, title: str, author: str, highlights: List[str], max_highlights: int = 10
    ) -> str:
        previous_summaries = []
        for highlight_group in batched(highlights, max_highlights):
            summary = self._generate_summary_prompt(
                title, author, highlight_group, previous_summaries
            )
            previous_summaries.append(summary)

        return previous_summaries[-1]

    def _generate_summary_prompt(
        self,
        title: str,
        author: str,
        highlights: List[str],
        previous_summaries: List[str],
    ) -> str:
        if previous_summaries:
            previous_summaries_text = "\n\n".join(previous_summaries)
        else:
            previous_summaries_text = "No previous summaries generated yet."

        """Generate a summary of the highlights."""
        prompt = f"""
        Generate a summary of the highlights from the book "{title}" by {author}.
        Do not loose the details or precision of the original text. Make sure to include all the details
        and account for the context of the previous summaries. Avoid generalities and generic statements.
        Use specific examples. Remember, you do not describe the book, you ONLY need 
        to include pieces of knowledge from the highlights in a organized way. 
        Use the following highlights and previous summaries:
        
        Previous summaries:
        {previous_summaries_text}
        
        Highlights:
        {highlights}

        Return only the summarized and organized pieces of knowledge, no other text.
        """
        return self.agent.run(prompt)

    def generate_tags(
        self,
        title: str,
        author: str,
        concepts: List[Dict[str, str]],
    ) -> List[Dict[str, str]]:

        concepts_text = "\n".join(
            [f"- {c['name']}: {c['description']}" for c in concepts]
        )

        prompt = f"""
        Create 5-10 specific and relevant tags for a note about the book "{title}" by {author}.
        
        Key concepts from the book:
        {concepts_text} 
        
        Generate tags that are specific rather than general. Use lowercase and hyphens for multi-word tags.
        Return only the tags, each prefixed with # and separated by spaces. Do not include the book title 
        nor the author in the tags. Make sure the tags are no longer than 2 words. You can use the estabilished 
        abbreviations when creating tags. Avoid creating generic tags like "history" or "science".
        """

        response = self.agent.run(prompt)

        # Extract tags from response
        return re.findall(r"#[a-zA-Z0-9_-]+", response)

    def create_obsidian_note(
        self,
        title: str,
        author: str,
        highlights: List[str],
        summary: str,
        concepts: List[Dict[str, str]],
        tags: List[str],
    ) -> str:
        """Create the content for an Obsidian note."""
        date = datetime.now().strftime("%Y-%m-%d")

        # Format concepts as markdown + tags
        concepts_md = "\n\n".join(
            [
                f"### {c['name']}\n#{'-'.join(c['name'].replace('*', '').split())} \n{c['description']}"
                for c in concepts
            ]
        )

        # Format highlights as markdown with quote blocks
        highlights_md = "\n\n".join([f"> {h}" for h in highlights])

        # Format tags
        tags_str = " ".join(tags)

        # Create the note content
        return f"""---
title: "{title}"
author: "{author}"
date: {date}
tags: {tags_str}
---

# {title}
*{author}*

## Summary

{summary}

## Key Concepts

{concepts_md}

## Highlights

{highlights_md}
"""

    def save_note(self, title: str, content: str) -> str:
        """Save the note to a file."""
        # Clean title for filename
        clean_title = re.sub(r'[\\/*?:"<>|]', "", title)
        clean_title = clean_title.replace(" ", "-")

        filename = f"{clean_title}.md"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return filepath

    def process_all_books(self, min_highlights: int = 3):
        """Process all books in the highlights file and create Obsidian notes."""
        author = "Unknown"  # Default
        for title, book_data in self.book_data.items():
            # Extract author (assuming format from kindle/notescrap.py
            # where title is stored with author)
            highlights = book_data["highlights"]
            author = book_data["author"]
            # Process highlights
            if highlights and len(highlights) >= min_highlights:
                print(f"Processing book: {title}")

                # Extract key concepts
                concepts = self.extract_key_concepts(title, author, highlights)
                print(f"Extracted concepts: {concepts}")
                # Enrich concepts if needed
                enriched_concepts = self.enrich_concepts(concepts)
                print(f"Enriched concepts: {enriched_concepts}")
                # Generate tags
                tags = self.generate_tags(title, author, enriched_concepts)
                print(f"Generated tags: {tags}")

                summary = self.generate_summary(title, author, highlights)
                # Create note
                note_content = self.create_obsidian_note(
                    title,
                    author,
                    highlights,
                    summary=summary,
                    concepts=enriched_concepts,
                    tags=tags,
                )

                # Save note
                filepath = self.save_note(title, note_content)
                print(f"Created note at: {filepath}")
            else:
                print(f"No highlights found for book: {title}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert Kindle highlights to Obsidian notes"
    )
    parser.add_argument(
        "--highlights",
        type=str,
        required=True,
        help="Path to Kindle highlights JSON file",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./obsidian_notes",
        help="Output directory for Obsidian notes",
    )
    parser.add_argument(
        "--model",
        type=str,
        # default="gpt-3.5-turbo",
        default="gpt-4o-mini",
        help="Model to use (HuggingFace model name or OpenAI model)",
    )

    args = parser.parse_args()

    agent = KindleToObsidianAgent(args.highlights, args.output, args.model)
    agent.process_all_books()


if __name__ == "__main__":
    main()
