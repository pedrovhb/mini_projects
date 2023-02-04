import asyncio
import os
import textwrap
from datetime import datetime
from pathlib import Path

import openai
import sqlite_utils

openai.api_key = os.environ["OPENAI_API_KEY"]
db = sqlite_utils.Database(Path(__file__).parent / "promptan.db")


async def code_complete(
    prompt: str,
    temperature: float = 0.5,
    top_p: float = 1,
    presence_penalty: float = 0,
    frequency_penalty: float = 0,
    stop: list[str] | None = None,
    best_of: int = 1,
    max_tokens: int = 600,
) -> str:
    response = await openai.Completion.acreate(
        engine="code-davinci-002",
        prompt=prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        stream=False,
        stop=stop or [],
        presence_penalty=presence_penalty,
        frequency_penalty=frequency_penalty,
        best_of=best_of,
        logprobs=5,
    )
    db["testing"].insert(
        {
            "prompt": prompt,
            "response": response.choices[0].text,
            "full_response": response,
            "timestamp": datetime.now().isoformat(),
        }
    )
    return response.choices[0].text


async def prompt_testing(code: str, path: str | Path | None = None) -> str:

    prompt = f"""
    {f"# Module path: {path}" if path else ""}
    We will write unit tests for the code below while thinking step by step what unit tests will be required for verifying that the code works as intended.

    ```python
    {code}
    ```

    The common usage cases of the code can be summarized as follows:

    <|start_summary|>
    1.
    """

    prompt = textwrap.dedent(prompt.strip())
    completions = await code_complete(prompt, stop=["<|end_summary|>"])

    print(completions)

    prompt_2 = f"""
    {prompt}{completions}\n    <|end_summary|>

    In addition to the above common usage cases, we can also think of the following edge cases:

    <|start_edge_cases|>
    1.
    """
    prompt_2 = textwrap.dedent(prompt_2.strip())

    completions_2 = await code_complete(prompt_2, stop=["<|end_edge_cases|>"])
    print(completions_2)

    prompt_3 = f"""
    {prompt_2}{completions_2}\n    <|end_edge_cases|>

    Now that we have a list of common usage cases and edge cases, we can write unit tests for the code.

    <|start_unit_tests|>
    ```python
    import pytest
    """
    prompt_3 = textwrap.dedent(prompt_3.strip())
    completions_3 = await code_complete(prompt_3, stop=["<|end_unit_tests|>", "```"])
    print(completions_3)

    final = f"""
    {prompt_3}{completions_3}\n    <|end_unit_tests|>
    ```
    """
    final = textwrap.dedent(final.strip())
    return final


if __name__ == "__main__":

    async def main() -> None:
        code = """
    def merge_async_iterables(*async_iters: AsyncIterable[_T]) -> Stream[_T]:

        async def _inner() -> AsyncIterator[_T]:
            futs: dict[asyncio.Future[_T], AsyncIterator[_T]] = {}
            for it in async_iters:
                async_it = aiter(it)
                fut = asyncio.ensure_future(anext(async_it))
                futs[fut] = async_it

            while futs:
                done, _ = await asyncio.wait(futs, return_when=asyncio.FIRST_COMPLETED)
                for done_fut in done:
                    try:
                        yield done_fut.result()
                    except StopAsyncIteration:
                        pass
                    else:
                        fut = asyncio.ensure_future(anext(futs[done_fut]))
                        futs[fut] = futs[done_fut]
                    finally:
                        del futs[done_fut]

        return Stream(_inner())
        """

        print(await prompt_testing(code))

    asyncio.run(main())
