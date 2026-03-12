from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    """
    Abstract interface for LLM chat completion.
    Implement this to add a new AI backend (OpenAI, Gemini, local vLLM, etc.).
    """

    @abstractmethod
    def chat_completion(self, messages, **kwargs):
        """
        Generate a chat completion from a list of message dicts.

        Args:
            messages: list of {"role": str, "content": str}
            **kwargs: provider-specific options (max_tokens, temperature, etc.)

        Returns:
            str – the assistant's response text.

        Raises:
            RuntimeError on unrecoverable failure.
        """

    @abstractmethod
    def chat_completion_with_context(self, messages, context_documents=None, **kwargs):
        """
        Generate a chat completion with optional RAG context injected.

        Args:
            messages: list of {"role": str, "content": str}
            context_documents: list of str – retrieved document chunks to prepend
            **kwargs: provider-specific options

        Returns:
            str – the assistant's response text.
        """


class BaseSTTProvider(ABC):
    """Abstract interface for Speech-to-Text."""

    @abstractmethod
    def transcribe(self, audio_file, language='en'):
        """
        Transcribe audio to text.

        Args:
            audio_file: file-like object containing audio data
            language: ISO 639-1 language code

        Returns:
            str – transcribed text

        Raises:
            RuntimeError on failure.
        """


class BaseTTSProvider(ABC):
    """Abstract interface for Text-to-Speech."""

    @abstractmethod
    def synthesize(self, text, voice='default'):
        """
        Convert text to speech audio.

        Args:
            text: string to synthesize
            voice: voice identifier (provider-specific)

        Returns:
            bytes – audio content

        Raises:
            RuntimeError on failure.
        """
