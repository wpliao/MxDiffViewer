# Keep real Mendix apps out of this repo; SonarQube is for our own code

This repo is public. Real Mendix apps used for testing, whether the user's own or a client's, and anything rendered from them must never be committed. Test fixtures must be apps created for the purpose and safe to publish.

"Test automation" means testing MxDiffViewer itself, with SonarQube on its code. Running or reporting on a Mendix app's own tests, and SonarQube scans of Mendix apps, are out of scope.
