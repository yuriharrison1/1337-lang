import logging
from leet_vm.types import Cogon

logger = logging.getLogger(__name__)

class ServiceProjector:
    """Calls leet-service via gRPC. Falls back to LocalProjector on failure."""

    def __init__(self, service_url: str = "localhost:50051"):
        self._url = service_url
        self._channel = None
        self._stub = None

    async def _connect(self):
        import grpc
        try:
            from leet_vm._proto import leet_pb2_grpc, leet_pb2  # noqa: F401
            self._channel = grpc.aio.insecure_channel(self._url)
            self._stub = leet_pb2_grpc.LeetServiceStub(self._channel)
            logger.info("ServiceProjector: connected to %s", self._url)
        except Exception as e:
            raise ConnectionError(f"leet-service unavailable at {self._url}: {e}")

    async def project(self, text: str, agent_id: str = "") -> Cogon:
        if not self._stub:
            await self._connect()
        from leet_vm._proto import leet_pb2
        req  = leet_pb2.EncodeRequest(text=text, agent_id=agent_id)
        resp = await self._stub.Encode(req)
        return Cogon(
            id=resp.cogon_id,
            sem=list(resp.sem),
            unc=list(resp.unc),
            stamp=resp.stamp,
        )

    async def decode(self, cogon: Cogon) -> str:
        if not self._stub:
            await self._connect()
        from leet_vm._proto import leet_pb2
        req  = leet_pb2.DecodeRequest(sem=cogon.sem, unc=cogon.unc)
        resp = await self._stub.Decode(req)
        return resp.text
