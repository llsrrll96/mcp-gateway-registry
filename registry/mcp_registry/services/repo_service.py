import subprocess
import shutil
import os
import re
import requests
import json
from pydantic import BaseModel
import asyncio
from typing import AsyncIterator


import logging
logger = logging.getLogger(__name__)


CALLBACK_URL="http://10.10.30.175:7860/api/mcp/callbacks/"
CLONE_PATH = "~/buildpack/"
IMAGE_URL = "docker.ifl.co.kr"
OCI_URL = "oci://docker.ifl.co.kr"
HELM_OPTION = "--insecure-skip-tls-verify"
GITLAB_PATH = "http://root:meta1234@datahub-dev-k8s-master/"
CHART_TEMPLATE_NAME="mcp-chart"
CHART_GITLAB_PATH = "http://root:meta1234@datahub-dev-k8s-master/mcp-server/"+CHART_TEMPLATE_NAME +".git"
REG_EX=r"^(kubectl .+)$"
project_full_path = "mcp-server/python-server/my-python-mcp"
project_full_name = "my-python-mcp"
user_id = ""
image_version = ""
mcp_server_port = 7000

class BuildResponse(BaseModel):
    id: str
    project_full_path: str
    project_full_name: str
    status: str
    version: str

class DeployResponse(BaseModel):
    project_full_path: str
    project_full_name: str
    status: str
    port: str

class RepoService:

    async def mcp_ci(self, project_full_path: str, project_full_name: str, id: str):
        ci_success = True
        try:
            git_clone_url = GITLAB_PATH + project_full_path + ".git"
            git_clone_shell = "git clone " + git_clone_url
            subprocess.run(git_clone_shell, shell=True)

            git_rev_shell = "git rev-parse HEAD"
            rev_dir = "./" + project_full_name
            commit_uid_cmd = subprocess.run(git_rev_shell, shell=True, capture_output=True, cwd=rev_dir, text=True)
            commit_uid = commit_uid_cmd.stdout.strip()
            print(commit_uid)

            image_full_name = IMAGE_URL + "/" + project_full_name + ":" + commit_uid
            docker_image_build_shell = "docker build -t " + image_full_name + " ./" + project_full_name
            subprocess.run(docker_image_build_shell, shell=True)

            docker_push_shell = "docker push " + image_full_name
            subprocess.run(docker_push_shell, shell=True)

            print("delete git clone directory = " + rev_dir)
            shutil.rmtree(rev_dir)

            logger.info('-----------------finish--ci-job--------------------------')
        except Exception as e:
            logger.error(f"mcp_ci: {str(e)}")
            ci_success = False

        if ci_success:
            yield "data: " + json.dumps({
                "status": "success",
                "data": {
                    "id": str(id),
                    "type": "ci",
                },
            }) + "\n\n"
        else:
            yield "data: " + json.dumps({
                "status": "failed",
                "data": {
                    "id": str(id),
                    "type": "ci",
                },
            }) + "\n\n"

    async def mcp_cd_k8s(self, project_full_name: str, version: str):


        logger.info('-----------------finish--cd-job--------------------------')


    # test
    async def run_ci(self, id: str) -> AsyncIterator[str]:
        # 진행 중 3스텝 예시

        # 실제 CI 성공/실패 판단 로직
        ci_success = True  # TODO: 실제 결과로 대체

        if ci_success:
            yield "data: " + json.dumps({
                "status": "success",
                "data": {
                    "id": str(id),
                    "type": "ci",
                },
            }) + "\n\n"
        else:
            yield "data: " + json.dumps({
                "status": "failed",
                "data": {
                    "id": str(id),
                    "type": "ci",
                },
            }) + "\n\n"

    async def run_cd(self, id:str) -> AsyncIterator[str]:
        for step in range(1, 3):
            yield f"data: {{\"status\": \"progress\", \"stage\": \"cd\", \"step\": {step}}}\n\n"
            await asyncio.sleep(1)


        yield "data: " + json.dumps({
            "status": "success",
            "data": {
                "id": str(id),
                "type": "cd",
            },
        }) + "\n\n"

# Global service instance
repo_service = RepoService()