/**
 * Searches all classes of .type-checkbox and builds a query string params.
 */
function searchParamsFromAlbumTypeChecks() {
    var all_checked = true;
    var search = "";

    $(".type-checkbox").each(function(i) {
        all_checked &= this.checked;
        search += (search ? "&" : "?") +
                  ("type=" + (this.checked ? this.name : ("!" + this.name)));
    });

    return !all_checked ? search : "";
}
