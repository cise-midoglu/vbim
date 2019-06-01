<!DOCTYPE html>
<html lang="en">
  <head>
    <title>VBIM: Shaka Player</title>
    <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/shaka-player/2.5.1/shaka-player.compiled.js"></script>
    <script type="text/javascript" src="https://cdn.bitmovin.com/analytics/web/2/bitmovinanalytics.min.js"></script>
  </head>
  <body>
        <p></p>

<!- ************************************************************************** ->
        <?php
        echo "title =                        " . $_GET["title"] . "<br>";
        echo "userId =                       " . $_GET["userId"] . "<br>";
        echo "videoId =                      " . $_GET["videoId"] . "<br><br>";

        echo "customData1 (cdnProvider) =    " . $_GET["customData1"] . "<br>";
        echo "customData2 (abrAlgorithm) =   " . $_GET["customData2"] . "<br>";
        echo "customData3 (experimentName) = " . $_GET["customData3"] . "<br>";
        echo "customData4 (containerVersion)=" . $_GET["customData4"] . "<br>";
        echo "customData5 (Monroe UUID) =    " . $_GET["customData5"] . "<br>";

        echo "cdnProvider =                  " . $_GET["cdnProvider"] . "<br>";
        echo "experimentName =               " . $_GET["experimentName"] . "<br>";
        ?>

        <script type="text/javascript">
        customData1 = '<?php echo $_GET["customData1"]; ?>' // cdnProvider
        customData2 = '<?php echo $_GET["customData2"]; ?>' // abrAlgorithm {abrDynamic / abrBola / abrThroughput}
        customData3 = '<?php echo $_GET["customData3"]; ?>' // experimentName
        customData4 = '<?php echo $_GET["customData4"]; ?>' // containerVersion
        customData5 = '<?php echo $_GET["customData5"]; ?>' // Monroe UUID

        title =       '<?php echo $_GET["title"]; ?>'
        userId =      '<?php echo $_GET["userId"]; ?>'
        videoId =     '<?php echo $_GET["videoId"]; ?>'

        cdnProvider = '<?php echo $_GET["cdnProvider"]; ?>'
        experimentName = '<?php echo $_GET["experimentName"]; ?>'

        abrAlgorithm = '<?php echo $_GET["customData2"]; ?>'
        </script>

        <center>

        Session ID: <input type="text" size="40" maxlength="15" id="sessionID" name="sID"/> <p></p>
        <script type="text/javascript">
          var sessionID = document.getElementById("sessionID");
        </script>
<!- ************************************************************************** ->

    <video id="video"
           width="640"  height="360"
           controls autoplay>
    </video>
    </center>
  
  <script>
  var manifestUri = 'https://cdn.bitmovin.com/analytics/test_assets/cise/Amazon-BBB-15bitrates-full/stream.mpd';

  function initApp() {
  // Install built-in polyfills to patch browser incompatibilities.
  shaka.polyfill.installAll();

  // Check to see if the browser supports the basic APIs Shaka needs.
  if (shaka.Player.isBrowserSupported()) {
    // Everything looks good!
    initPlayer();
  } else {
    // This browser does not have the minimum set of APIs we need.
    console.error('Browser not supported!');
  }
}

function initPlayer() {
  // Create a Player instance.
  var video = document.getElementById('video');
  var player = new shaka.Player(video);

  // Bitmovin Analytics
                  var analyticsConfig = {
                    key: "",  // enter analytics license key here
                    title: title,
                    userId: userId,
                    videoId: videoId,
                    customData1: customData1,
                    customData2: customData2,
                    customData3: customData3,
                    customData4: customData4,
                    customData5: customData5,
                    cdnProvider: cdnProvider,
                    experimentName: experimentName
                  }
  myAdapter = new bitmovin.analytics.adapters.ShakaAdapter(analyticsConfig, player);

  // Attach player to the window to make it easy to access in the JS console.
  window.player = player;

  // Listen for error events.
  player.addEventListener('error', onErrorEvent);

  // Try to load a manifest.
  // This is an asynchronous process.
  player.load(manifestUri).then(function() {
    // This runs if the asynchronous load is successful.
    console.log('The video has now been loaded!');
  }).catch(onError);  // onError is executed if the asynchronous load fails.

   sID = myAdapter.getCurrentImpressionId()
   console.log("sessionID = ", sID)
   sessionID.value = sID
}

function onErrorEvent(event) {
  // Extract the shaka.util.Error object from the event.
  onError(event.detail);
}

function onError(error) {
  // Log the error.
  console.error('Error code', error.code, 'object', error);
}

document.addEventListener('DOMContentLoaded', initApp);

  </script>

  </body>
</html>
