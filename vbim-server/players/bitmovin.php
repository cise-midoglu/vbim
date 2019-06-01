<!DOCTYPE html>
<html lang="en">
<head>
    <title>VBIM: Bitmovin Player</title>
    <meta charset="UTF-8"/>
    <meta http-equiv="X-UA-Compatible" content="IE=edge,chrome=1">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script type="text/javascript" src="https://cdn.bitmovin.com/player/web/8.9.0/bitmovinplayer.js"></script>
    <script type="text/javascript" src="https://cdn.bitmovin.com/analytics/web/2.3.0/bitmovinanalytics.min.js"></script>
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


<div id="player"></div>
<script type="text/javascript">
console.log("TITLE --->", title);

var qualitySwitches = -1;
const conf = {

    key: "", // enter player license key here
    analytics: {
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
        },

                playback: {
						autoplay:  true,
						muted:     false
				},

  				style: {
						width: '640px',
						height: '360px',
						controls: true
			    },



	events: {
        videodownloadqualitychange : function() {
            ++qualitySwitches;
                console.log("adaptation --->", qualitySwitches);
        },

        play : function(e) {
                initTime = new Date().getTime();
                console.log("PLAY --->", initTime);
        },

        stallstarted : function(e) {

                console.log("STALL --->", initTime);
        },
	}
};

const source = {
   dash: 'https://cdn.bitmovin.com/analytics/test_assets/cise/Amazon-BBB-15bitrates-full/stream.mpd'
};

var player = new bitmovin.player.Player(document.getElementById('player'), conf);
var analytics = new bitmovin.analytics.adapters.Bitmovin8Adapter(player);

sessionID.value = player.analytics.getCurrentImpressionId();

player.load(source).then(() => {
  //player.play();
}).catch((reason) => {
  console.error('player setup failed', reason);
});

</script>

</body>
</html>
