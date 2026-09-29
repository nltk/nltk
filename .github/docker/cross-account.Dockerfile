# The shape of nltk/nltk#3928, run for real in CI: the image is built as root,
# which installs the data, and runs as an unprivileged user that must read it.
# The build uses this checkout, not a release, so the branch under test is
# what the container runs.
FROM python:3.11-slim
COPY . /src
RUN pip install --no-cache-dir /src
# The reporter's unchanged commands: no flag, a root install extracts on its own.
RUN python -m nltk.downloader -d /usr/local/lib/nltk_data stopwords
RUN python -m nltk.downloader -d /usr/local/lib/nltk_data wordnet
RUN python -m nltk.downloader -d /usr/local/lib/nltk_data omw-1.4
RUN ls -la /usr/local/lib/nltk_data/corpora
RUN useradd -m appuser
USER appuser
ENV NLTK_DATA=/usr/local/lib/nltk_data
COPY --chmod=0444 .github/docker/cross-account-check.py /home/appuser/check.py
CMD ["python", "/home/appuser/check.py"]
