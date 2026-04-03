from tools.face_capture import TOOL_SPEC as FACE_CAPTURE_SPEC, execute as face_capture_execute
from tools.liveness import TOOL_SPEC as LIVENESS_SPEC, execute as liveness_execute
from tools.keycloak_auth import TOOL_SPEC as KEYCLOAK_SPEC, execute as keycloak_execute
from tools.verify_identity import TOOL_SPEC as VERIFY_SPEC, execute as verify_identity_execute
from tools.register_face import TOOL_SPEC as REGISTER_FACE_SPEC, execute as register_face_execute

# Login flow tools
LOGIN_TOOLS = [FACE_CAPTURE_SPEC, LIVENESS_SPEC, VERIFY_SPEC, KEYCLOAK_SPEC]

# Registration flow tools
REGISTRATION_TOOLS = [FACE_CAPTURE_SPEC, LIVENESS_SPEC, REGISTER_FACE_SPEC, KEYCLOAK_SPEC]

# Handler registry (used by both agents; image_b64 + embedding injected at dispatch time)
TOOL_HANDLERS = {
    "validate_face_capture": face_capture_execute,
    "detect_liveness": liveness_execute,
    "issue_keycloak_token": keycloak_execute,
    "verify_identity": verify_identity_execute,
    "register_face": register_face_execute,
}
