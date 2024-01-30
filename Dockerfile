FROM registry.gitlab.com/gitlab-data/data-image/data-image:latest

# Install the package
RUN mkdir ./amber-data-utils
COPY . ./amber-data-utils
RUN pip install -e ./amber-data-utils
WORKDIR ./amber-data-utils

