jQuery.fn.unitalIframeUrl = ->
  $element = @
  url = $element.data('url')
  if url and url != 'example.com'
    $.get("/get_iframe_url/#{btoa(url)}", (data) ->
      iframe_url = data['iframe_url']
      if iframe_url
        $iframe = $("<iframe src='#{iframe_url}' style='height:685px;width:1018px;max-width: 100%;'></iframe>")
        $element.after($iframe)
      else
        console.error "Cannot fetch iframe's address. Perhaps you entered invalid url?"
    )
