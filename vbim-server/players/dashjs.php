<!DOCTYPE html>
<html lang="en">
    <head>
        <title>VBIM: Dash.js Player</title>
        <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/dashjs/2.9.3/dash.all.min.js"></script>
        <script type="text/javascript" src="https://cdn.bitmovin.com/analytics/web/2/bitmovinanalytics.min.js"></script>
        <style>
            video {
                width: 640px;
                height: 360px;
            }
        </style>
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


        <div>
            <video id="videoPlayer" autoplay controls></video>
        </div>
        <script>
            (function(){
                var url = "https://cdn.bitmovin.com/analytics/test_assets/cise/Amazon-BBB-15bitrates-full/stream.mpd";
                var analyticsConfig = {
                    key: "", // enter analytics license key here
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

                    var video = document.getElementById('videoPlayer');
                    var time = new Date().getTime();
                    var dashjsPlayer = dashjs.MediaPlayer().create();
                    myAdapter = new bitmovin.analytics.adapters.DashjsAdapter(analyticsConfig, dashjsPlayer, {starttime: time});
                    dashjsPlayer.initialize(video, url, false);
                    sID = myAdapter.getCurrentImpressionId()
                    console.log("sessionID = ", sID)
                    sessionID.value = sID;

                    console.log("ABR logic = ", dashjsPlayer.getABRStrategy()); //"abrDynamic", "abrBola" or "abrThroughput"

                    if (abrAlgorithm == "abrThroughput" || abrAlgorithm == "abrBola") {
                        dashjsPlayer.setABRStrategy(abrAlgorithm);
                        console.log("ABR logic = ", dashjsPlayer.getABRStrategy());
                    }

            })();

        </script>
        </center>
    </body>
</html>
