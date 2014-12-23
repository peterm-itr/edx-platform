jQuery(function($) {
    $('a.dropdown').click(function(e){
        e.preventDefault();
        $(this).siblings('.dropdown-menu').toggle();
    });
});