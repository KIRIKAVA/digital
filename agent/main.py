import time
import requests
import os
import logging
import subprocess
import socket
import json
from typing import Dict, Any, List
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class NetworkChecker:
    @staticmethod
    def ping_check(target: str) -> Dict[str, Any]:
        """ICMP ping check"""
        try:
            result = subprocess.run(
                ["ping", "-c", "3", "-W", "5", target],
                capture_output=True,
                text=True,
                timeout=10
            )
            success = result.returncode == 0
            response_time = None
            if success:
                for line in result.stdout.splitlines():
                    if "avg" in line:
                        parts = line.split("/")
                        if len(parts) >= 5:
                            try:
                                response_time = round(float(parts[4].split()[0]), 2)
                            except (ValueError, IndexError):
                                pass
                        break
            return {
                "success": success,
                "response_time": int(response_time) if response_time else None,
                "stdout": result.stdout if not success else None,
                "avg_rtt": response_time,
                "min_rtt": None,
                "max_rtt": None
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Ping timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def http_check(target: str) -> Dict[str, Any]:
        """HTTP check"""
        try:
            start_time = time.time()
            if not target.startswith(('http://', 'https://')):
                url = f"http://{target}"
            else:
                url = target
            response = requests.get(url, timeout=10, allow_redirects=True)
            response_time = round((time.time() - start_time) * 1000, 2)
            return {
                "success": 200 <= response.status_code < 400,
                "status_code": response.status_code,
                "response_time": int(response_time),
                "url": response.url,
                "content_length": len(response.content),
                "final_url": response.url
            }
        except requests.exceptions.Timeout:
            return {"success": False, "error": "HTTP request timeout"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "Connection failed"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def tcp_check(target: str, port: int = 80) -> Dict[str, Any]:
        """TCP port check"""
        try:
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((target, port))
            response_time = round((time.time() - start_time) * 1000, 2)
            sock.close()
            return {
                "success": result == 0,
                "port": port,
                "response_time": int(response_time),
                "status": "open" if result == 0 else "closed"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def dns_check(target: str, record_type: str = "A") -> Dict[str, Any]:
        """DNS record check"""
        try:
            import dns.resolver
            start_time = time.time()
            resolver = dns.resolver.Resolver()
            resolver.timeout = 5
            resolver.lifetime = 5
            answers = resolver.resolve(target, record_type)
            response_time = round((time.time() - start_time) * 1000, 2)
            records = [str(rdata) for rdata in answers]
            return {
                "success": True,
                "records": records,
                "response_time": int(response_time),
                "record_type": record_type
            }
        except Exception as e:
            return {"success": False, "error": str(e), "record_type": record_type}


class Agent:
    def __init__(self):
        self.backend_url = os.getenv("BACKEND_URL", "http://backend:8000")
        self.token = os.getenv("AGENT_TOKEN", "secret123")
        self.name = os.getenv("AGENT_NAME", "docker-agent-1")
        self.agent_id = None
        self.checker = NetworkChecker()

    def get_location(self):
        try:
            resp = requests.get("https://ipinfo.io/json", timeout=3)
            data = resp.json()
            return f"{data.get('city', 'Unknown')}, {data.get('country', 'XX')}"
        except:
            return "docker"

    def register_agent(self):
        location = self.get_location()
        try:
            response = requests.post(
                f"{self.backend_url}/agents/register",
                json={
                    "name": self.name,
                    "location": location,
                    "token": self.token
                },
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                self.agent_id = data.get('id')
                logger.info(f"✅ Agent registered: {self.name} (ID: {self.agent_id}, Location: {location})")
                return True
            else:
                logger.info(f"ℹ️ Agent registration status: {response.status_code}")
                return True
        except Exception as e:
            logger.error(f"❌ Registration error: {e}")
            return False

    def send_heartbeat(self):
        try:
            response = requests.post(
                f"{self.backend_url}/agents/{self.name}/heartbeat",
                timeout=5
            )
            logger.debug(f"💓 Heartbeat: {response.status_code}")
            return True
        except Exception as e:
            logger.error(f"❌ Heartbeat failed: {e}")
            return False

    def get_pending_checks(self):
        try:
            response = requests.get(f"{self.backend_url}/checks/", timeout=10)
            if response.status_code == 200:
                all_checks = response.json()
                pending_checks = [
                    check for check in all_checks
                    if check.get('status') == 'pending'
                ]
                logger.info(f"📋 Found {len(pending_checks)} pending checks")
                return pending_checks
            else:
                logger.error(f"❌ Failed to get checks: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"❌ Error getting checks: {e}")
            return []

    def perform_single_check(self, check_type: str, target: str) -> Dict[str, Any]:
        logger.info(f"   Performing {check_type} check for {target}...")
        try:
            if check_type == 'ping':
                result = self.checker.ping_check(target)
            elif check_type == 'http':
                result = self.checker.http_check(target)
            elif check_type == 'https':
                result = self.checker.http_check(f"https://{target}")
            elif check_type == 'tcp':
                result = self.checker.tcp_check(target, 80)
            elif check_type.startswith('dns_'):
                record_type = check_type.split('_')[1].upper()
                result = self.checker.dns_check(target, record_type)
            else:
                result = {"success": False, "error": f"Unknown check type: {check_type}"}
            status_icon = "✅" if result.get("success") else "❌"
            error_msg = result.get("error", "")
            logger.info(f"     {check_type}: {status_icon} {error_msg}")
            return result
        except Exception as e:
            logger.error(f"     ❌ Error in {check_type}: {e}")
            return {"success": False, "error": str(e)}

    def perform_check(self, check_data: dict):
        target = check_data['target']
        check_types = check_data['check_types']
        check_id = check_data['id']
        logger.info(f"🔍 Starting checks for {target}: {check_types}")
        results = []
        for check_type in check_types:
            result_data = self.perform_single_check(check_type, target)
            formatted_result = {
                "check_type": check_type,
                "success": result_data.get("success", False),
                "result_data": result_data,
                "response_time": result_data.get("response_time"),
                "error_message": result_data.get("error")
            }
            results.append(formatted_result)
        success = self.submit_results(check_id, results)
        if success:
            logger.info(f"🎉 Completed check {check_id}")
        else:
            logger.error(f"💥 Failed to submit results for {check_id}")

    def submit_results(self, check_id: str, results: List[dict]) -> bool:
        try:
            payload = {
                "check_id": check_id,
                "agent_name": self.name,
                "results": results,
                "completed_at": datetime.now().isoformat()
            }
            response = requests.post(
                f"{self.backend_url}/results/",
                json=payload,
                timeout=10
            )
            if response.status_code == 200:
                logger.info(f"📤 Submitted {len(results)} results for check {check_id}")
                return True
            else:
                logger.error(f"❌ Submit failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Error submitting results: {e}")
            return False

    def process_checks(self):
        pending_checks = self.get_pending_checks()
        if not pending_checks:
            logger.info("😴 No pending checks")
            return
        for check in pending_checks:
            logger.info(f"  📝 Check ID: {check['id']}, Target: {check['target']}")
            self.perform_check(check)

    def run(self):
        logger.info(f"🚀 Starting Host Checker Agent: {self.name}")
        logger.info(f"🔗 Backend URL: {self.backend_url}")
        for attempt in range(3):
            if self.register_agent():
                break
            logger.warning(f"⚠️ Registration attempt {attempt + 1} failed")
            time.sleep(2)
        cycle_count = 0
        while True:
            cycle_count += 1
            try:
                logger.info(f"🔄 Agent cycle #{cycle_count}")
                self.send_heartbeat()
                self.process_checks()
                logger.info(f"💤 Cycle #{cycle_count} completed, waiting 15s...")
            except Exception as e:
                logger.error(f"💥 Error in cycle #{cycle_count}: {e}")
            time.sleep(15)


if __name__ == "__main__":
    logger.info("⏳ Waiting 10s for backend...")
    time.sleep(10)
    agent = Agent()
    agent.run()