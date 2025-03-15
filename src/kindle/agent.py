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
from functools import lru_cache

load_dotenv()


class KindleToObsidianAgent:
    def __init__(
        self,
        highlights_file: str,
        output_dir: str,
        model_name: str = "gpt-4o-mini",
        openai_api_key: str = os.getenv("OPENAI_API_KEY"),
        log_file: str = None,
    ):
        """Initialize the agent with the path to highlights file and output directory."""
        self.highlights_file = highlights_file
        self.output_dir = output_dir
        self.model_name = model_name
        self.openai_api_key = openai_api_key
        
        # Set up log file
        self.log_file = log_file or os.path.join(output_dir, "processing_log.txt")

        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Clear log file if it exists
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(f"Kindle to Obsidian Processing Log - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
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

    def log(self, message):
        """Write a message to the log file and also print it to console."""
        print(message)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"{message}\n")

    def extract_key_concepts(
        self, title: str, author: str, highlights: List[str]
    ) -> List[Dict[str, str]]:
        """Extract key concepts from the book highlights with source references."""
        highlights_text = "\n\n".join(
            [f"[{i+1}] {h}" for i, h in enumerate(highlights)]
        )
        prompt = f"""
        Analyze these highlights from the book "{title}" by {author}. 
        Identify 5-10 key concepts or ideas presented in the text.
        For each concept, provide a brief description based on the highlights.
        
        IMPORTANT: For each concept, include references to the highlight numbers that support this concept.
        Use the format (ref: [1], [3], [5]) at the end of each description to cite your sources.
        
        HIGHLIGHTS:
        {highlights_text}
        
        Return your answer as a list of concepts with descriptions including highlight references.
        """

        response = self.agent.run(prompt)

        # Parse response into structured concepts
        concepts = []
        # Enhanced pattern to capture references
        concept_pattern = r"(?:^|\n)(?:- |•\s*|[0-9]+\.\s*)([^:]+):\s*(.+?)(?:\(ref: ((?:\[[0-9]+\](?:, )?)+)\))?(?=\n(?:- |•\s*|[0-9]+\.\s*)|$)"
        matches = re.finditer(concept_pattern, response, re.MULTILINE | re.DOTALL)

        for match in matches:
            concept = {
                "name": match.group(1).strip(),
                "description": match.group(2).strip(),
            }

            # Extract references if present
            if match.group(3):
                ref_numbers = re.findall(r"\[([0-9]+)\]", match.group(3))
                # Convert to zero-based indices (for array access)
                concept["references"] = [int(num) - 1 for num in ref_numbers]
            else:
                concept["references"] = []

            concepts.append(concept)

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
        """Generate a summary of the highlights with citations."""
        if previous_summaries:
            previous_summaries_text = "\n\n".join(previous_summaries)
        else:
            previous_summaries_text = "No previous summaries generated yet."

        prompt = f"""
        Generate a summary of the highlights from the book "{title}" by {author}.
        Do not loose the details or precision of the original text. Make sure to include all the details
        and account for the context of the previous summaries. Avoid generalities and generic statements.
        Use specific examples. Remember, you do not describe the book, you ONLY need 
        to include pieces of knowledge from the highlights in a organized way.
        
        IMPORTANT: For each main point in your summary, include references to the specific highlight numbers 
        that support this point. Use the format (ref: [1], [3], [5]) at the end of each paragraph to cite your sources.
        
        Use the following highlights and previous summaries:
        
        Previous summaries:
        {previous_summaries_text}
        
        Highlights:
        {" ".join([f"[{i+1}] {h}" for i, h in enumerate(highlights)])}

        Return only the summarized and organized pieces of knowledge with citations, no other text.
        """
        return self.agent.run(prompt)

    def parse_summary_references(self, summary: str) -> Dict[str, List[int]]:
        """Extract references from the summary text."""
        paragraphs = {}
        # Split by paragraphs and process each one
        for i, para in enumerate(summary.split('\n\n')):
            # Check if the paragraph has references
            ref_match = re.search(r'\(ref: ((?:\[[0-9]+\](?:, )?)+)\)', para)
            if ref_match:
                # Extract the paragraph content without the reference part
                content = para.replace(ref_match.group(0), '').strip()
                # Extract reference numbers
                ref_numbers = re.findall(r'\[([0-9]+)\]', ref_match.group(1))
                # Convert to zero-based indices (for array access)
                references = [int(num) - 1 for num in ref_numbers]
                paragraphs[f"para_{i}"] = {"content": content, "references": references}
            else:
                paragraphs[f"para_{i}"] = {"content": para, "references": []}
        
        return paragraphs

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
        """Create the content for an Obsidian note with citations."""
        date = datetime.now().strftime("%Y-%m-%d")

        # Parse the summary to extract references
        parsed_summary = self.parse_summary_references(summary)
        
        # Format summary with citations
        summary_md = []
        for _, para_data in parsed_summary.items():
            para_text = para_data["content"]
            
            # Add references if available
            if para_data["references"]:
                # Create links to the highlight section
                ref_links = []
                for ref_idx in para_data["references"]:
                    if 0 <= ref_idx < len(highlights):
                        # Create a link to the highlight in the format ^highlight-N
                        ref_links.append(f"[[#^highlight-{ref_idx + 1}]]")
            
                if ref_links:
                    para_text += f" (Sources: {', '.join(ref_links)})"
            
            summary_md.append(para_text)
        
        summary_md = "\n\n".join(summary_md)

        # Format concepts as markdown + tags with citations
        concepts_md = []
        for c in concepts:
            concept_text = (
                f"### {c['name']}\n#{'-'.join(c['name'].replace('*', '').replace(",", "").replace(".", "").replace("'", "").lower().split())}"
                f" \n{c['description']}"
            )

            # Add references if available
            if "references" in c and c["references"]:
                # Create links to the highlight section
                ref_links = []
                for ref_idx in c["references"]:
                    if 0 <= ref_idx < len(highlights):
                        # Create a link to the highlight in the format ^highlight-N
                        ref_links.append(f"[[#^highlight-{ref_idx + 1}]]")

                if ref_links:
                    concept_text += f"\n\nSources: {', '.join(ref_links)}"

            concepts_md.append(concept_text)

        concepts_md = "\n\n".join(concepts_md)

        # Format highlights as markdown with quote blocks and unique IDs for linking
        highlights_md = []
        for i, highlight in enumerate(highlights):
            # Add a unique ID to each highlight for referencing
            highlights_md.append(f"> {highlight} ^highlight-{i + 1}")

        highlights_md = "\n\n".join(highlights_md)

        # Format tags
        tags_str = " ".join(tags)

        # Create the note content
        return f"""---
title: "{title}"
author: "{author.replace('by: ', '').replace('By: ', '').replace('By:', '').replace('by:', '').strip()}"
date: {date}
tags: {tags_str}
---

# {title}
*{author}*

## Summary

{summary_md}

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

    def prepare_book_data(
        self, title: str, author: str, highlights: List[str], min_highlights: int = 3
    ):
        """Prepare all the data needed for a book note, which can be cached."""
        # Convert highlights list to tuple since lists are not hashable for caching
        highlights_tuple = tuple(highlights)
        return self._prepare_book_data_impl(
            title, author, highlights_tuple, min_highlights
        )

    # @lru_cache(maxsize=None)
    def _prepare_book_data_impl(
        self, title: str, author: str, highlights_tuple: tuple, min_highlights: int = 3
    ):
        """Implementation of prepare_book_data that works with hashable types."""
        # Convert tuple back to list for processing
        highlights = list(highlights_tuple)

        if not highlights or len(highlights) < min_highlights:
            return None

        self.log(f"Processing book: {title}")

        # Extract key concepts
        concepts = self.extract_key_concepts(title, author, highlights)
        self.log(f"Extracted concepts: {concepts}")

        # Enrich concepts if needed
        enriched_concepts = self.enrich_concepts(concepts)
        self.log(f"Enriched concepts: {enriched_concepts}")

        # Generate tags
        tags = self.generate_tags(title, author, enriched_concepts)
        self.log(f"Generated tags: {tags}")

        # Generate summary
        summary = self.generate_summary(title, author, highlights)
        self.log(f"Generated summary of {len(summary.split())} words")

        return {
            "title": title,
            "author": author,
            "highlights": highlights,
            "summary": summary,
            "concepts": enriched_concepts,
            "tags": tags,
        }

    def process_all_books(self, min_highlights: int = 3):
        """Process all books in the highlights file and create Obsidian notes."""
        for title, book_data in self.book_data.items():
            # Add a separator for each book in the log
            separator = f"\n\n#### {title} ####\n"
            self.log(separator)
            
            highlights = book_data["highlights"]
            author = book_data.get("author", "Unknown")

            # This part can be cached
            prepared_data = self.prepare_book_data(
                title, author, highlights, min_highlights
            )

            if prepared_data:
                # Create note (this part uses the cached data)
                note_content = self.create_obsidian_note(
                    prepared_data["title"],
                    prepared_data["author"],
                    prepared_data["highlights"],
                    summary=prepared_data["summary"],
                    concepts=prepared_data["concepts"],
                    tags=prepared_data["tags"],
                )

                # Save note
                filepath = self.save_note(title, note_content)
                self.log(f"Created note at: {filepath}")
            else:
                self.log(f"No highlights found for book: {title}")
            
            self.log("\n" + "-" * 80)  # Add a line after each book's processing


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
        default="gpt-4o-mini",
        help="Model to use (HuggingFace model name or OpenAI model)",
    )
    parser.add_argument(
        "--log",
        type=str,
        help="Path to log file (defaults to 'processing_log.txt' in output directory)",
    )

    args = parser.parse_args()

    agent = KindleToObsidianAgent(
        args.highlights, 
        args.output, 
        args.model, 
        log_file=args.log
    )
    agent.process_all_books()


if __name__ == "__main__":
    main()
