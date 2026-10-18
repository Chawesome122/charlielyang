
//<script>
      var weblinkHeadlines = {
          wl_numberHdPerPage:20,
          wl_url: "https://wcsecure.weblink.com.au/Clients/lynascorp/HeadlineJsonP.aspx",
          wl_head: document.head,
          wl_urlWithParam: "",
          wl_hdGroup: 0,
          wl_year: 0,
          wl_MaxNumberOfTabs:5,
          wl_maxYear: 0,
          wl_minYear:0,
          wl_pageNumber:1,
          wl_firstTab:null,
          wl_lastTab:null,
          wl_maxWidth: 0,
          wl_hideElem: 0,
          wl_hiddenYears: "",
          wl_all_Page: "",
          wl_symbol:"",
          wl_maxDisplayedPages: 10,
          wl_search: ""
          ,wl_justDidSearch:false
      };
      weblinkHeadlines.catOptions = [
          { name: "All Announcements", value: 0 }
          , { name: "Presentations", value: 4 }
         // , { name: "Quarterly Reports", value: 3 }
          , { name: "Annual Reports", value: 1 }
           , { name: "Reports", value: 3 }
          ];

      weblinkHeadlines.requestWeblinkData = function (pageNumber, year) {
          weblinkHeadlines.wl_year = year;
          weblinkHeadlines.wl_pageNumber = pageNumber;
          var script = document.createElement("script");
          var additionalParam = "?numberHdPerPage=";
          var url = window.location.href;
          if (url.indexOf("hdGroup=") > -1) {
              if (url.indexOf("hdGroup=annual") > -1)
                  additionalParam = "?hdGroup=1&numberHdPerPage=";
              else if (url.indexOf("hdGroup=half") > -1)
                  additionalParam = "?hdGroup=2&numberHdPerPage=";
              else if (url.indexOf("hdGroup=quarterly") > -1)  // else if (url.indexOf("hdGroup=quarterly") > -1)
                  additionalParam = "?hdGroup=3&numberHdPerPage=";
              else if (url.indexOf("hdGroup=presentations") > -1)
                  additionalParam = "?hdGroup=4&numberHdPerPage=";
              else if (url.indexOf("hdGroup=reports") > -1)
                  additionalParam = "?hdGroup=5&numberHdPerPage=";
              else if (url.indexOf("hdGroup=esg") > -1)
                  additionalParam = "?hdGroup=6&numberHdPerPage=";
          }
          if (additionalParam.indexOf("hdGroup") == -1) {
              weblinkHeadlines.wl_all_Page = true;
              var wl_catOptions = document.getElementById("wl_catOptions");
              if(wl_catOptions)
              {
                  var selectedGroup = wl_catOptions.options[wl_catOptions.selectedIndex].value;
                  additionalParam = "?hdGroup=" + selectedGroup + "&numberHdPerPage=";
                  weblinkHeadlines.wl_hdGroup = selectedGroup;
              }              
          }
          else
              weblinkHeadlines.wl_all_Page = false;



          //weblinkHeadlines.wl_urlWithParam = weblinkHeadlines.wl_url + additionalParam + weblinkHeadlines.wl_numberHdPerPage + "&pageNumber=" + weblinkHeadlines.wl_pageNumber + "&year=" + weblinkHeadlines.wl_year;          
          //--- used this below line for serach option
          weblinkHeadlines.wl_urlWithParam = weblinkHeadlines.wl_url + additionalParam + weblinkHeadlines.wl_numberHdPerPage + "&pageNumber=" + weblinkHeadlines.wl_pageNumber + "&year=" + weblinkHeadlines.wl_year +"&search="+weblinkHeadlines.wl_search;
          script.setAttribute("src", weblinkHeadlines.wl_urlWithParam);
          if (weblinkHeadlines.wl_head != null) {
              weblinkHeadlines.wl_head.appendChild(script);
              weblinkHeadlines.wl_head.removeChild(script);
          }
          else {
              if (window.jQuery) {
                  // jQuery is loaded  
                  if ($.support.cors) {
                      // your code
                  } else {
                      $.ajax({
                          type: 'GET',
                          url: weblinkHeadlines.wl_urlWithParam,
                          dataType: 'jsonp',
                          data: {
                              callback: '?'
                          },
                          success: function (data) {
                              var featureJSON = data.feature;

                          },
                          error: function (e) {
                              //alert("error"+e.toString());
                          },
                          complete: function () {

                          }
                      });
                  }
              } else {
                  // jQuery is not loaded
                  alert("Please import jQuery.");
              }

          }
      }


      function wl_headlinesFunction(data, totalHeadlines, maxYear, minYear) {
          if (data == null) {
              return;
          }
          var d = data;
          var tp = totalHeadlines;
          weblinkHeadlines.wl_maxYear = maxYear.maxYear;
          weblinkHeadlines.wl_minYear = minYear.minYear;
          weblinkHeadlines.wl_renderTab();
          weblinkHeadlines.wl_renderHeadlineTable(data, totalHeadlines.totalHeadlines);
          weblinkHeadlines.wl_renderPageNavigation(totalHeadlines.totalHeadlines);

          //------- Added serach

          $('#wl-input-search').keydown(function (e) {
              if (e.keyCode == 13) {
                  weblinkHeadlines.searchBtnClicked();
                  e.preventDefault();
              }              
          });
         
          if (weblinkHeadlines.wl_justDidSearch)
          {
              $(".wl-input-search").focus();
              $(".wl-input-search").select();
              weblinkHeadlines.wl_justDidSearch = false;
          }

          //----end search 



          if(document.getElementsByClassName)
          {
              var tabElements = document.getElementsByClassName("top-tabs");
              if(tabElements.length > 1)
              {
                  weblinkHeadlines.wl_firstTab = tabElements[0];
                  weblinkHeadlines.wl_lastTab = tabElements[tabElements.length-1];
              }
              weblinkHeadlines.wl_CheckResponsiveTabs();
          }
          else
          {
              wl_tabUL.style.display = "none";
              wl_CatOptionsDiv.style.display = "block";
              wl_YearOptionsDiv.style.display = "block";
          }
          weblinkHeadlines.checkHeight();
      }
      weblinkHeadlines.wl_CheckResponsiveTabs = function () {         
          var $wl_tabUL = $("#wl_tabUL");
          var $wl_CatOptionsDiv = $("#wl_CatOptionsDiv");
          var tabCount = $("#wl_tabUL li").length - weblinkHeadlines.wl_hideElem;
          var $wl_firstTab = $wl_tabUL.find("li:first-child");
          var $wl_lastTab = $wl_tabUL.find("li:nth-child(" + tabCount + ")");          
          var keepChecking = true;
          var count = 1;
          var tempObj;
          while (keepChecking) {
              tempObj = $wl_tabUL.find("li:nth-child(" + count + ")");
              if (tempObj.length > 0 && tempObj[0].style.display != "none") {
                  $wl_lastTab = tempObj;
              }
              if (tempObj.length == 0)
                  break;
              if (count > 10)
                  break;
              count++;
          }
          if ($wl_firstTab != null && $wl_lastTab != null) {
              if ( true || tabCount < $("#wl_tabUL li").length) {
                  var $wl_recentHiddenTab = $wl_tabUL.find("li:nth-child(" + (tabCount + 1) + ")");
                  //console.log("SPACE = %s", $(window).width() - ($wl_tabUL.outerWidth() + $wl_CatOptionsDiv.outerWidth()))
                  if (($(window).width() - ($wl_tabUL.outerWidth() + $wl_CatOptionsDiv.outerWidth())) >= ($wl_firstTab.outerWidth() + 12)) {
                      // console.log("Display recent HIDDEN tab");
                      for (var j = 1; j < $("#wl_tabUL li").length + 5; j++) {
                          tempObj = $wl_tabUL.find("li:nth-child(" + j + ")");
                          if (tempObj.length > 0 && tempObj[0].style.display == "none") {
                              tempObj[0].style.display = "inline-block";
                              break;
                          }
                      }
                  }
              }
              if ($wl_firstTab.position().top != $wl_lastTab.position().top) {
                  if ($wl_lastTab.hasClass("active"))
                      $wl_lastTab = $wl_tabUL.find("li:nth-child(" + (tabCount - 1) + ")");
                  for (var j = $("#wl_tabUL li").length + 5; j > 0; j--) {
                      tempObj = $wl_tabUL.find("li:nth-child(" + j + ")");
                      if (tempObj.length > 0 && !tempObj.hasClass("active") && tempObj[0].style.display != "none") {
                          tempObj[0].style.display = "none";
                          break;
                      }
                  }
              }
          }
      }
      if(window.addEventListener)
      {
          window.addEventListener("resize",function(){
              weblinkHeadlines.wl_CheckResponsiveTabs();
          });
      }
      weblinkHeadlines.wl_renderPageNavigation = function (totalHeadlines) {
          var wl_nav = document.getElementById("wl_nav");
          var contents = "";
          var totalPage = Math.ceil(totalHeadlines / weblinkHeadlines.wl_numberHdPerPage);
          if (totalPage == 1) {
              wl_nav.innerHTML = "";
              return;
          }
        //  if (totalPage == 1) {                 
        //        return;
        //  }
          //contents += "<nav class='navigation paging-navigation row' role='navigation'>";
          contents += "     <h1 class='screen-reader-text'></h1>";
          contents += "     <div class='nav-links large-12 columns'>";
          contents += "         <div class='wp-pagenavi'>";
          // NEW 2015/02/10
          if (totalPage == 0) {
              contents += "             <span class='no-headline'>There are currently no announcements for this category</span>";
          } else {
              //contents += "             <span class='wl_pages'>Page " + weblinkHeadlines.wl_pageNumber + " of " + totalPage + "</span>";
          }
          
          // NEW 2015/02/10
          var className = "page larger";
          if (weblinkHeadlines.wl_pageNumber > 1) {
              //contents += " <a class='page larger' href='javascript:weblinkHeadlines.requestWeblinkData(" + (weblinkHeadlines.wl_pageNumber -1)+ "," + weblinkHeadlines.wl_hdGroup + ")'><<</a>";
              contents += " <a class='page larger' href='javascript:weblinkHeadlines.requestWeblinkData(" + (weblinkHeadlines.wl_pageNumber -1)+ "," + weblinkHeadlines.wl_year +  ")'>&#8592;</a>";
          }
          var startPage = weblinkHeadlines.wl_findStartPage(weblinkHeadlines.wl_pageNumber,totalPage);
          if(startPage != 1) 
          {
              contents += " <a class='page larger' href='javascript:weblinkHeadlines.requestWeblinkData("+1+","+weblinkHeadlines.wl_hdGroup+")'>" + 1 + "</a>..";
          }          
          var endPage = startPage + weblinkHeadlines.wl_maxDisplayedPages - 1;
          if (startPage > 1)
              endPage++;
          if(endPage > totalPage)
              endPage = totalPage;
          for (var i = startPage; i <= endPage; i++) {
              if (weblinkHeadlines.wl_pageNumber == i)
                  contents += "<span class='current'>" + i + "</span>";
              else
                  //contents += " <a class='page larger' href='javascript:weblinkHeadlines.requestWeblinkData("+i+","+weblinkHeadlines.wl_hdGroup+")'>" + i + "</a>";
                  contents += " <a class='page larger' href='javascript:weblinkHeadlines.requestWeblinkData(" + i + "," + weblinkHeadlines.wl_year + ")'>" + i + "</a>";
              
          }
          if (weblinkHeadlines.wl_pageNumber < totalPage) {
              //contents += " <a class='page larger' href='javascript:weblinkHeadlines.requestWeblinkData(" + (weblinkHeadlines.wl_pageNumber + 1) + "," + weblinkHeadlines.wl_hdGroup + ")'>&#8594;</a>";
              contents += " <a class='page larger' href='javascript:weblinkHeadlines.requestWeblinkData(" + (weblinkHeadlines.wl_pageNumber +1)+ "," + weblinkHeadlines.wl_year + ")'>&#8594;</a>";
          }
          contents += "         </div>";
          contents += "     </div>";
          //contents += "</nav>";
          wl_nav.innerHTML = contents;
          // old code---
          /*
          for (var i = 1; i <= totalPage; i++) {
              if (i > 1) {
                  contents += "<span class='wl-divider'></span>";
              }
              if (weblinkHeadlines.wl_pageNumber == i)
                  //contents += "<span class='current'>" + weblinkHeadlines.twoDigit(i) + "</span>";
                  contents += "<span class='current'>" + i + "</span>";
              else
                  //contents += " <a class='page larger' href='javascript:weblinkHeadlines.requestWeblinkData(" + i + "," + weblinkHeadlines.wl_year + ")'>" + weblinkHeadlines.twoDigit(i) + "</a>";
                  contents += " <a class='page larger' href='javascript:weblinkHeadlines.requestWeblinkData(" + i + "," + weblinkHeadlines.wl_year + ")'>" + i + "</a>";

          }
          if (weblinkHeadlines.wl_pageNumber < totalPage) {
              contents += "<span class='wl-divider'></span>";
              contents += " <a class='page larger' href='javascript:weblinkHeadlines.requestWeblinkData(" + (totalPage) + "," + weblinkHeadlines.wl_year + ")'>Last</a>";
          }
          contents += "         </div>";
          contents += "     </div>";
          
          //contents += "</nav>";
          wl_nav.innerHTML = contents;
         // $(".wl-divider").html("|");
         */
      }

      weblinkHeadlines.wl_findStartPage = function(selectedPage,totalPage)
      {
          var startPage = 1+(Math.floor(selectedPage / weblinkHeadlines.wl_maxDisplayedPages) * weblinkHeadlines.wl_maxDisplayedPages);
          if(startPage + weblinkHeadlines.wl_maxDisplayedPages > totalPage)
              startPage = totalPage-weblinkHeadlines.wl_maxDisplayedPages;
          else if(startPage==0)
              startPage = 1;
          else
              startPage = startPage-1;
          if(startPage<=0)
              startPage =1;
          return startPage;
      }

      weblinkHeadlines.twoDigit = function (val) {
          if (val > 9)
              return val;
          return "0" + val;
      }

      weblinkHeadlines.wl_renderHeadlineTable=function(data, totalPage) {
          var wl_headlineDiv = document.getElementById("wl_headlineDiv");
          var contents = "<div class='displaying-results-div'></div>";
          contents += "<table class=\"wl_headlineTable\">";
          /*contents +="		<thead>";
          contents +="			<tr>";
          contents += "  			<td class=\"wl_headerCol wl_DateCol\">Date</td>";
          contents +="				<td colspan=2 class=\"wl_headerCol wl_NewsCol\">Announcements</td>";
          contents +="			</tr>";
          contents += "		</thead>";*/
          var headline;
          var headlineDatetime;
          var dateTimeJson = "";
          var year = 0;
          var canSvg = !!(document.createElementNS && document.createElementNS('http://www.w3.org/2000/svg', 'svg').createSVGRect);
          var ext = canSvg?".svg":".png";          
          var firstTD = " wl-first-td";
          var month = -1;
          for (var i = 0; i < data.headlines.length; i++) {
              headline = data.headlines[i];
              dateTimeJson = headline.datetime.substring(6);
              headlineDatetime = new Date(parseInt(dateTimeJson));
              if (year != headlineDatetime.getFullYear()) {
                  year = headlineDatetime.getFullYear();
                  //if(year < weblinkHeadlines.wl_maxYear - weblinkHeadlines.wl_MaxNumberOfTabs)
                  //  contents += " <tr><td class='wl_date' colspan='2'>" + year + "</td></tr>";
              }
              if (month != headlineDatetime.getMonth()) {
                  month = headlineDatetime.getMonth();
                  var extraTxt = "";
                  //if (WHNcount == 1)
                  //    extraTxt = "<div class='title-div'>Announcements released as WHL Energy Ltd</div>"
                  contents += " <tr><td class='wl_date' colspan='3'>" + extraTxt + headlineDatetime.format("mmmm") + "</td></tr>";
              }
              contents += "<tr class='wl-data-tr'>"
              //contents += " <!--<td class='wl_dateTD'>" + weblinkHeadlines.wl_formatDate(headlineDatetime) + "</td>-->";
              //contents += " <td class='wl_imgTD" + firstTD + "'><a href='" + headline.pdfLink + "' class='wl-pdf-link'><img class='wl-pdf-img' src='images/folder-dl-icon" + ext + "'/></a></td>";
              if (false && window.location.href.indexOf("hdGroup") > -1) {
                  contents += " <td class='wl_dataTD" + firstTD + "'><div class='wl_headlineLinkDiv'><a class='wl_headlineLink' href='" + headline.pdfLink + "' title='" + headline.HeadlineText + "' target='_blank'>" + weblinkHeadlines.wl_formatDate(headlineDatetime)+" - " + headline.HeadlineText + "</a></div>"
              }
              else {
                  contents += " <td class='wl-date-td" + firstTD + "'>" + "<div class='wl-date-div1'>" + weblinkHeadlines.wl_formatDate(headlineDatetime) + "</div>" + "</td>";
                  contents += " <td class='wl-date-td" + firstTD + "'>" + "<div class='wl-date-div2'>" + weblinkHeadlines.wl_formatDate2(headlineDatetime) + "</div>" + "</td>";
                  contents += " <td class='wl_dataTD" + firstTD + "'><div class='wl_headlineLinkDiv'><a class='wl_headlineLink' href='" + headline.pdfLink + "' title='" + headline.HeadlineText + "' target='_blank'>" + headline.HeadlineText + "</a></div>"
              }
              //contents += "     <div class='wl-date-div'>" + weblinkHeadlines.wl_formatDate(headlineDatetime) + "</div>";
              contents += "  </td>";
              contents += " <td class='wl_imgTD"+firstTD+"'><span class='wl-size-span'>" + weblinkHeadlines.formatFileSize(headline.fileSize) + "</span></td>";
              contents += "</tr>";
              firstTD = "";
          }
          contents += "</table>";
          wl_headlineDiv.innerHTML += contents;
      }
      weblinkHeadlines.formatFileSize = function (value) {
          if (value / 1000 > 0.9 && value/1000 < 900)
              return (value / 1000).toFixed(0) + "kb";
          else if(value/1000000 >0.8)
              return (value / 1000000).toFixed(0) + "mb";
          return value;
              
      }
      weblinkHeadlines.wl_formatDate=function(dt)
      {
          return dt.format("d mmmm yyyy");
      }

      weblinkHeadlines.wl_formatDate2=function(dt)
      {
          return dt.format("d mmm yyyy");
      }
      weblinkHeadlines.wl_renderTab=function() {
          var wl_headlineDiv = document.getElementById("wl_headlineDiv");
          var contents = "<table id='wl_yearSelectionTable'><tr class='wl-tab-tr'><td class='wl_tabTD'>";
          contents += "<ul id='wl_tabUL' class=\"medium-12 tabs\">";
          var active = "";
          var tabCount = 0;
          var renderingYear = weblinkHeadlines.wl_maxYear;
          if (renderingYear == 0)
              renderingYear = (new Date().getFullYear());
          if (weblinkHeadlines.wl_maxYear < weblinkHeadlines.wl_year)
              weblinkHeadlines.wl_year = weblinkHeadlines.wl_maxYear;
          while (tabCount < weblinkHeadlines.wl_MaxNumberOfTabs) {
              active = "";
              if (weblinkHeadlines.wl_year == 0 && tabCount == 0) {
                  active = "active";
              }
              else if (renderingYear == weblinkHeadlines.wl_year)
                  active = "active";
              contents += "  <li class=\"top-tabs " + active + "\"><a class='wl_headlineLink wl_titleTab' href=\"javascript:weblinkHeadlines.requestWeblinkData(1," + renderingYear + ")\">" + renderingYear + "</a></li>";
              renderingYear--;
              tabCount++;             
              if (renderingYear < weblinkHeadlines.wl_minYear || weblinkHeadlines.wl_minYear == 0)
                  break;
          }
          if (weblinkHeadlines.wl_year> 0 && renderingYear >= weblinkHeadlines.wl_year) {
              contents += "  <li class=\"top-tabs active\"><a class='wl_headlineLink wl_titleTab' href=\"javascript:weblinkHeadlines.requestWeblinkData(1," + weblinkHeadlines.wl_year + ")\">" + weblinkHeadlines.wl_year + "</a></li>";
          }
          contents += "</ul></td>";
          contents += "<td id='wl_dropdownTD'><div class='wl-dropdown-div' id='wl_CatOptionsDiv'>";          
          
          if (weblinkHeadlines.wl_all_Page)
          {              
              contents += " <span class='wl-select wl-select-cat'><select class='wl-dropdown' onchange='weblinkHeadlines.wl_onCatOptionsChange();' id='wl_catOptions'>";
              var opt
              for (var i = 0; i < weblinkHeadlines.catOptions.length; i++) {
                  opt = weblinkHeadlines.catOptions[i];
                  contents += "<option value='" + opt.value + "'" + (weblinkHeadlines.wl_hdGroup == opt.value ? "selected" : "") + ">" + opt.name + "</option>";
              }
              contents += "</select></span>";
          }

          contents += "  <span class='wl-select wl-select-year'><select class='wl-dropdown' onchange='weblinkHeadlines.wl_onYearOptionsChange();' id='wl_yearOptions' style=''>";
         
          for (var i = weblinkHeadlines.wl_maxYear; i >= weblinkHeadlines.wl_minYear; i--) {
              renderingYear = i;
              if (renderingYear == 0)
                  renderingYear = (new Date().getFullYear());
              contents += "<option value='" + i + "'" + (weblinkHeadlines.wl_year == renderingYear ? "selected" : "") + ">" + renderingYear + "</option>";
          }
          contents += "     </select/></span>";

          contents += "</div></td></tr></table>";     
          // added search 
          if (weblinkHeadlines.wl_all_Page) {
              contents += weblinkHeadlines.wl_generateSearchHtml();
          }
          if (wl_headlineDiv != undefined) {
              wl_headlineDiv.innerHTML = contents;
          }
          weblinkHeadlines.wl_hideElem = 0;
          weblinkHeadlines.wl_CheckResponsiveTabs();
      }

      //--- added for search
      weblinkHeadlines.wl_generateSearchHtml = function () {
          var contents = "<div class='wl-main-search'>";
          contents += "<span class='wl-search-lbl'>Keyword search</span>";
          contents += "<input type='text' name='wl-input-search' id='wl-input-search' class='wl-input-search' value='"+weblinkHeadlines.wl_search+"'/>";
          contents += "<a class='wl-search-btn' href='javascript:weblinkHeadlines.searchBtnClicked()'>Search</a>";
          contents += "</div>";
          return contents;
      }
      weblinkHeadlines.searchBtnClicked = function () {
          var searchTxt = $(".wl-input-search").val();
          if(weblinkHeadlines.wl_search != searchTxt)
          {
              weblinkHeadlines.wl_search = searchTxt;
              weblinkHeadlines.requestWeblinkData(1, weblinkHeadlines.wl_year);
              weblinkHeadlines.wl_justDidSearch = true;
          }          
      }

      //-- end search

      weblinkHeadlines.wl_onCatOptionsChange = function () {
          weblinkHeadlines.wl_year = 0;
          weblinkHeadlines.wl_onYearOptionsChange(true);
      }

      weblinkHeadlines.wl_onYearOptionsChange = function(resetYear)
      {
          var wl_yearOptions = document.getElementById("wl_yearOptions");
          if (wl_yearOptions.style.display !== "none")
          {
              var selectedGroup = wl_yearOptions.options[wl_yearOptions.selectedIndex].value;
              var _y = parseInt(selectedGroup);
              if (resetYear)
                  _y = 0;
              weblinkHeadlines.requestWeblinkData(1, _y);
          }
      }

      var wlQuote = {};
      wlQuote.firstDisplay = true;
      weblinkHeadlines.checkHeight = function () {
          var body = document.body,
              html = document.documentElement;

          var height = body.offsetHeight;
          height = document.getElementById("wl_headlineDiv").clientHeight + document.getElementById("wl_nav").clientHeight
          if (height < 150)
              height = height + 55;
          var url = window.location.href;
          var additionalParam = "";
          if (url.indexOf("hdGroup=") > -1) {
              if (url.indexOf("hdGroup=annual") > -1)
                  additionalParam = "?hdGroup=annual";
              else if (url.indexOf("hdGroup=half") > -1)
                  additionalParam = "?hdGroup=half";
              else if (url.indexOf("hdGroup=quarterly") > -1)   //hdGroup=quarterly
                  additionalParam = "?hdGroup=quarterly";       //hdGroup=quarterly        
              else if (url.indexOf("hdGroup=presentations") > -1)
                  additionalParam = "?hdGroup=presentations";
              else if (url.indexOf("hdGroup=reports") > -1)
                  additionalParam = "?hdGroup=reports";
               else if (url.indexOf("hdGroup=esg") > -1)
                  additionalParam = "?hdGroup=esg";
          }
          //additionalParam = "";
          if (wlQuote.firstDisplay) {
              wlQuote.firstDisplay = false;
              setTimeout(function () {
                  parent.postMessage("h:" + (height + 25) + "|src:headlineContents.aspx"+additionalParam+"|frameid: ", '*');
              }, 500);
          }
          else
              parent.postMessage("h:" + (height + 25) + "|src:headlineContents.aspx"+additionalParam+"|frameid: ", '*');
      };
      if (window.addEventListener)
          window.addEventListener("resize", weblinkHeadlines.checkHeight);
      //</script>