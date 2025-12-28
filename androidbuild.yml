name: Build Android APK
on:
  push:
    branches: [ main, master ]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      # Nettoyage pour gagner de la place
      - name: Free Disk Space
        run: |
          sudo rm -rf /usr/share/dotnet
          sudo rm -rf /opt/ghc
          sudo rm -rf "/usr/local/share/boost"
          sudo rm -rf "$AGENT_TOOLSDIRECTORY"

      # Compilation avec Buildozer Action
      - name: Build with Buildozer
        uses: ArtemSBulgakov/buildozer-action@v1
        id: buildozer
        with:
          command: buildozer android debug
          buildozer_version: master

      # Envoi de l'APK fini
      - name: Upload APK
        uses: actions/upload-artifact@v4  # Mise à jour v4
        with:
          name: package
          path: bin/*.apk
          
