FROM registry.gitlab.com/gitlab-data/data-image/data-image:latest

# Install the package
RUN mkdir ./gitlab-data-utils
COPY . ./gitlab-data-utils
RUN pip install -e ./gitlab-data-utils
WORKDIR ./gitlab-data-utils

